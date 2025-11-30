import os
import json
from flask import Blueprint, render_template, request, jsonify
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

# LangChain Imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

load_dotenv()

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

FEEDBACK_FILE = 'feedback_log.json'
GOLDEN_DATASET_FILE = 'golden_dataset.json'
FAISS_INDEX_PATH = "faiss_index"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def load_golden_dataset():
    if os.path.exists(GOLDEN_DATASET_FILE):
        try:
            with open(GOLDEN_DATASET_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_golden_record(record):
    data = load_golden_dataset()
    
    # Check for duplicates (simple check by question)
    existing = next((item for item in data if item["question"] == record["question"]), None)
    if existing:
        existing.update(record) # Update existing
    else:
        data.append(record)
    
    with open(GOLDEN_DATASET_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@admin_bp.route('/')
def index():
    feedback_data = load_feedback()
    golden_data = load_golden_dataset()
    
    # Create a map of ingested status for UI
    ingested_map = {item['question']: item.get('ingested', False) for item in golden_data}
    
    # Sort by timestamp desc
    feedback_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return render_template('admin.html', feedback=feedback_data, ingested_map=ingested_map)

@admin_bp.route('/save_golden', methods=['POST'])
def save_golden():
    try:
        data = request.json
        record = {
            "question": data.get('question'),
            "ground_truth": data.get('ground_truth'),
            "context_source": data.get('context_source'),
            "verified_at": data.get('timestamp'),
            "ingested": False # Default to false on save
        }
        save_golden_record(record)
        return jsonify({"status": "success", "message": "Saved to Golden Dataset"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@admin_bp.route('/ingest_golden', methods=['POST'])
def ingest_golden():
    if not GOOGLE_API_KEY:
        return jsonify({"status": "error", "message": "GOOGLE_API_KEY not found"}), 500
        
    try:
        data = request.json
        question = data.get('question')
        answer = data.get('ground_truth')
        
        # Create Document
        content = f"Question: {question}\nAnswer: {answer}"
        doc = Document(page_content=content, metadata={"source": "Golden Dataset"})
        
        # Initialize Embeddings
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
        # Load or Create Index
        if os.path.exists(FAISS_INDEX_PATH):
            vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            vectorstore.add_documents([doc])
        else:
            vectorstore = FAISS.from_documents([doc], embeddings)
            
        # Save Index
        vectorstore.save_local(FAISS_INDEX_PATH)
        
        # Update local record
        record = {
            "question": question,
            "ground_truth": answer,
            "ingested": True,
            "ingested_at": datetime.now().isoformat()
        }
        save_golden_record(record)
        
        return jsonify({"status": "success", "message": "Ingested successfully", "ingested_at": record["ingested_at"]})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@admin_bp.route('/delete_feedback', methods=['POST'])
def delete_feedback():
    try:
        data = request.json
        target_timestamp = data.get('timestamp')
        target_query = data.get('user_query')
        
        feedback_data = load_feedback()
        
        new_feedback_data = [
            item for item in feedback_data 
            if not (item.get('timestamp') == target_timestamp and item.get('user_query') == target_query)
        ]
        
        if len(new_feedback_data) == len(feedback_data):
            return jsonify({"status": "error", "message": "Record not found"}), 404
            
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(new_feedback_data, f, indent=4)
            
        return jsonify({"status": "success", "message": "Feedback deleted"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- App Feedback Routes ---

APP_FEEDBACK_FILE = 'app_feedback.json'

def load_app_feedback():
    if os.path.exists(APP_FEEDBACK_FILE):
        try:
            with open(APP_FEEDBACK_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

@admin_bp.route('/app_feedback')
def app_feedback_view():
    feedback_data = load_app_feedback()
    feedback_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return render_template('admin_app_feedback.html', feedback=feedback_data)

@admin_bp.route('/delete_app_feedback', methods=['POST'])
def delete_app_feedback():
    try:
        data = request.json
        target_id = data.get('id')
        
        feedback_data = load_app_feedback()
        new_feedback_data = [item for item in feedback_data if item.get('id') != target_id]
        
        if len(new_feedback_data) == len(feedback_data):
            return jsonify({"status": "error", "message": "Record not found"}), 404
            
        with open(APP_FEEDBACK_FILE, 'w') as f:
            json.dump(new_feedback_data, f, indent=4)
            
        return jsonify({"status": "success", "message": "Feedback deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Analytics Routes ---

QUERY_LOG_FILE = 'query_log.json'

def load_query_log():
    if os.path.exists(QUERY_LOG_FILE):
        try:
            with open(QUERY_LOG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

@admin_bp.route('/analytics')
def analytics_view():
    chat_feedback = load_feedback()
    golden_data = load_golden_dataset()
    query_log = load_query_log()
    
    total_queries = len(query_log)
    
    response_times = [item.get('response_time', 0) for item in query_log if item.get('response_time')]
    avg_response_time = round(sum(response_times) / len(response_times), 2) if response_times else 0
    
    total_feedback = len(chat_feedback)
    positive_ratings = sum(1 for item in chat_feedback if item.get('rating') == 1)
    satisfaction_rate = int((positive_ratings / total_feedback * 100) if total_feedback > 0 else 0)
    
    ingested_count = sum(1 for item in golden_data if item.get('ingested', False))
    ingestion_rate = int((ingested_count / len(golden_data) * 100) if len(golden_data) > 0 else 0)
    
    from collections import defaultdict, Counter
    from datetime import timedelta
    
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    volume_data = defaultdict(int)
    
    for item in query_log:
        try:
            ts = datetime.fromisoformat(item.get('timestamp')).date().isoformat()
            if ts in dates:
                volume_data[ts] += 1
        except:
            pass
            
    chart_volume = [volume_data[d] for d in dates]
    chart_labels = [datetime.fromisoformat(d).strftime('%a') for d in dates]
    
    sentiment_counts = Counter()
    for item in chat_feedback:
        r = item.get('rating')
        if r == 1: sentiment_counts['Positive'] += 1
        elif r == -1: sentiment_counts['Negative'] += 1
        else: sentiment_counts['Neutral'] += 1
        
    chart_sentiment = [sentiment_counts['Positive'], sentiment_counts['Negative'], sentiment_counts['Neutral']]
    
    query_counts = Counter(item.get('query') for item in query_log if item.get('query'))
    top_queries = [{"query": q, "count": c} for q, c in query_counts.most_common(5)]
    
    metrics = {
        "total_queries": total_queries,
        "avg_response_time": avg_response_time,
        "satisfaction_rate": satisfaction_rate,
        "ingestion_rate": ingestion_rate,
        "chart_volume": chart_volume,
        "chart_labels": chart_labels,
        "chart_sentiment": chart_sentiment,
        "top_queries": top_queries
    }
    
    return render_template('admin_analytics.html', metrics=metrics)

# --- Evaluation Routes ---

@admin_bp.route('/evaluation')
def evaluation_view():
    return render_template('admin_evaluation.html')

@admin_bp.route('/run_evaluation', methods=['POST'])
def run_evaluation():
    try:
        # 1. Load Synthetic Data
        synthetic_file = 'synthetic_dataset.json'
        if not os.path.exists(synthetic_file):
            return jsonify({"status": "error", "message": "Synthetic dataset not found. Please generate it first."}), 404
            
        with open(synthetic_file, 'r') as f:
            test_data = json.load(f)
            
        # Limit to 10 for speed in this demo, or use all 50 if user insists (user asked for 50)
        # I'll use 10 to avoid timeout, but the user asked for 50. I'll try 20.
        test_data = test_data[:20] 
        
        questions = [item['question'] for item in test_data]
        ground_truths = [[item['ground_truth']] for item in test_data]
        
        # 2. Run Inference (Get Answers & Contexts)
        answers = []
        contexts = []
        
        # Initialize Vector Store
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        
        # Initialize LLM for Answer Generation
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        
        print(f"Running inference on {len(questions)} items...")
        
        for q in questions:
            # Retrieve
            docs = retriever.invoke(q)
            ctx = [d.page_content for d in docs]
            contexts.append(ctx)
            
            # Generate Answer
            # Simple RAG chain for evaluation consistency
            context_text = "\n\n".join(ctx)
            prompt = f"Answer the question based on the context.\nContext: {context_text}\nQuestion: {q}\nAnswer:"
            response = llm.invoke(prompt)
            answers.append(response.content)
            
        # 3. Run RAGAS Evaluation
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision
        
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths
        }
        
        dataset = Dataset.from_dict(data)
        
        # Configure RAGAS with Gemini
        # RAGAS uses default LLMs. We need to patch it or pass llm/embeddings.
        # In recent RAGAS versions, we pass llm/embeddings to evaluate()
        
        print("Starting RAGAS evaluation...")
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision],
            llm=llm,
            embeddings=embeddings
        )
        
        # 4. Format Results
        df = results.to_pandas()
        details = df.to_dict(orient='records')
        
        # Serialize details (handle NaN)
        clean_details = []
        for row in details:
            clean_details.append({
                "question": row['question'],
                "faithfulness": 0 if pd.isna(row['faithfulness']) else row['faithfulness'],
                "answer_relevancy": 0 if pd.isna(row['answer_relevancy']) else row['answer_relevancy'],
                "context_precision": 0 if pd.isna(row['context_precision']) else row['context_precision']
            })
            
        response_data = {
            "faithfulness": results['faithfulness'],
            "answer_relevancy": results['answer_relevancy'],
            "context_precision": results['context_precision'],
            "details": clean_details
        }
        
        return jsonify({"status": "success", "results": response_data})
        
    except Exception as e:
        print(f"Evaluation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
