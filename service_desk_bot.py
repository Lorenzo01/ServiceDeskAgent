# service_desk_bot.py
"""
Service Desk Chatbot core logic using Google Gemini with manual ReAct loop.
"""
import os
import logging
import json
from dotenv import load_dotenv

# --- LANGCHAIN IMPORTS ---
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FAISS_INDEX_PATH = "faiss_index"

# Global Clients
vectorstore = None
llm = None

def init_clients():
    global vectorstore, llm
    
    print("DEBUG: Initializing Gemini clients...")
    
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not found.")
        print("DEBUG: GOOGLE_API_KEY not found.")
        return

    try:
        # Initialize Embeddings (needed to load FAISS)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
        # Load FAISS Index
        if os.path.exists(FAISS_INDEX_PATH):
            vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            print("DEBUG: FAISS index loaded successfully.")
        else:
            print("DEBUG: FAISS index not found. Please run ingest_data.py.")

        # Initialize LLM
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        print("DEBUG: Gemini LLM initialized.")
        
    except Exception as e:
        logger.error(f"Init failed: {e}")
        print(f"DEBUG: Client init failed: {e}")

init_clients()

# --- 1. DEFINE THE TOOL ---

@tool
def lookup_guides(query: str) -> str:
    """
    Useful for finding information about Macquarie University policies, procedures, guidelines, and rules.
    Input should be a specific search query (e.g., 'Computer security procedure' or 'it misuse').
    Returns a text summary of the relevant document passages.
    """
    print(f"DEBUG: Agent is searching for: {query}")
    
    if not vectorstore:
        return "Error: Knowledge base not loaded. Please contact admin."

    try:
        # Run Search
        results = vectorstore.similarity_search(query, k=5)

        # Format results for the Agent to read
        results_text = []
        for r in results:
            content = r.page_content
            source = r.metadata.get('source', 'Unknown')
            snippet = f"Source: {source}\nContent: {content}"
            results_text.append(snippet)
        
        if not results_text:
            return "No relevant documents found in the database."
            
        return "\n\n".join(results_text)
    except Exception as e:
        print(f"DEBUG: Search tool error: {e}")
        return f"Error during search: {str(e)}"

# --- 2. MANUAL AGENT LOOP ---

def format_chat_history(history_list):
    """Converts list of dicts [{'role': 'user', 'content': '...'}, ...] to string."""
    formatted = []
    for msg in history_list[-6:]: # Keep last 6 messages for context
        role = "User" if msg['role'] == 'user' else "Assistant"
        content = msg.get('content', '')
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)

def ask_service_desk_stream(user_query: str, chat_history: list = None, dev_settings: dict = None):
    """
    Generator that yields events:
    {'type': 'log', 'content': '...'} -> Thinking/Action updates
    {'type': 'answer', 'content': '...'} -> Final answer
    """
    if dev_settings is None: dev_settings = {}
    if chat_history is None: chat_history = []
    
    formatted_history = format_chat_history(chat_history)
    collected_sources = []
    
    if not llm:
        yield {"type": "error", "content": "LLM not initialized."}
        return

    try:
        # Bind tools to LLM
        tools = [lookup_guides]
        llm_with_tools = llm.bind_tools(tools)
        
        # System Prompt
        system_message = """
        ### IDENTITY & SCOPE
        You are the **Macquarie University Policy Central Assistant**.
        Your ONLY purpose is to assist staff and students with questions about University policies, procedures, guidelines, and rules based on the provided knowledge base.

        **GUARDRAIL:** If the user asks about non-policy topics (like general IT support, weather, or personal advice), politely REFUSE and direct them to the appropriate department if known, or state you are only for Policy inquiries.

        **CONTEXT:**
        - **Policy Central** is the sole authoritative source for all Macquarie University policies.
        - If you cannot find an answer, advise the user to contact the **Policy team in Governance Services** at **policy@mq.edu.au**.

        **CRITICAL INSTRUCTIONS:**
        1. **CHECK FIRST:** Before searching, check if the answer is already in the 'Previous Conversation'.
        2. **ONE SEARCH IS USUALLY ENOUGH:** Do not run multiple searches for synonyms unless the first search failed completely.
        3. **NO HALLUCINATIONS:** If the tools return no relevant results, admit it immediately.

        ### OUTPUT FORMATTING RULES
        When providing your 'Final Answer':
        - **Structure:** Use clear headings, bullet points, and numbered steps.
        - **Citations:** You MUST cite sources (policy names) if available.
        - **Escalation:** If you cannot answer, say: "I cannot answer this based on the available policy documents. Please contact the Policy team at policy@mq.edu.au."
        """

        messages = [
            HumanMessage(content=f"{system_message}\n\nPrevious Conversation:\n{formatted_history}\n\nQuestion: {user_query}")
        ]

        # Manual Loop (max 5 steps)
        for step in range(5):
            print(f"\n--- Step {step + 1} ---")
            
            # Yield planning thought
            if step == 0:
                yield {"type": "log", "content": "Planning: Analyzing user request and checking context..."}
            
            # Invoke LLM
            print(f"DEBUG: Invoking LLM with {len(messages)} messages...")
            response = llm_with_tools.invoke(messages)
            print(f"DEBUG: LLM Response: {response}")
            messages.append(response)

            # Check for tool calls
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    tool_id = tool_call['id']
                    
                    # Agentic Thought Log
                    log_msg = f"Action: Decided to use tool '{tool_name}' to find information about '{tool_args.get('query', 'unknown')}'."
                    print(f"AGENT ACTION: {log_msg}")
                    yield {"type": "log", "content": log_msg}
                    
                    # Execute tool
                    if tool_name == "lookup_guides":
                        # Extract query from args (it might be a dict or object)
                        query = tool_args.get('query')
                        yield {"type": "log", "content": f"Execution: Searching knowledge base for '{query}'..."}
                        tool_result = lookup_guides.invoke(query)
                    else:
                        tool_result = f"Error: Tool {tool_name} not found."
                    
                    print(f"TOOL RESULT: {str(tool_result)[:500]}...")
                    
                    # Extract sources from tool result
                    try:
                        lines = str(tool_result).split('\n')
                        for line in lines:
                            if line.startswith("Source: "):
                                source_name = line.replace("Source: ", "").strip()
                                if source_name and source_name not in collected_sources:
                                    collected_sources.append(source_name)
                    except Exception as e:
                        print(f"DEBUG: Error extracting sources: {e}")

                    # Observation Log
                    if "No relevant documents" in str(tool_result):
                         yield {"type": "log", "content": "Observation: No relevant documents found. I may need to refine my search."}
                    else:
                         yield {"type": "log", "content": f"Observation: Found relevant policy information. Synthesizing answer..."}
                    
                    # Append tool result to messages
                    print("DEBUG: Appending ToolMessage...")
                    messages.append(ToolMessage(content=tool_result, tool_call_id=tool_id))
                    print("DEBUG: ToolMessage appended.")
            
            # Force exit if max steps reached
            if step == 4:
                 print("AGENT: Max steps reached, giving up.")
                 yield {"type": "answer", "content": "I apologize, but I am unable to find a specific answer after multiple attempts. Please contact the Service Desk for further assistance.", "needs_email_support": True}
                 return
            else:
                # Final Answer
                final_answer = response.content
                
                # Handle list-based content (common in newer Gemini versions)
                if isinstance(final_answer, list):
                    text_parts = []
                    for part in final_answer:
                        if isinstance(part, dict) and 'text' in part:
                            text_parts.append(part['text'])
                        elif isinstance(part, str):
                            text_parts.append(part)
                    final_answer = "".join(text_parts)
                
                if not response.tool_calls:
                    print(f"AGENT ANSWER: {str(final_answer)[:200]}...")
                    
                    # Final thought before answer
                    yield {"type": "log", "content": "Finalizing: Formulating response based on retrieved policies."}
                    
                    needs_support = "I cannot answer" in final_answer
                    yield {
                        "type": "answer", 
                        "content": final_answer, 
                        "needs_email_support": needs_support,
                        "sources": collected_sources
                    }
                    return

    except Exception as e:
        logger.error(f"Agent Error: {e}")
        yield {"type": "error", "content": str(e)}

def ask_service_desk(user_query: str, dev_settings: dict = None) -> dict:
    # Simple wrapper around the stream for legacy calls
    response = {"answer": "", "sources": [], "needs_email_support": False}
    for event in ask_service_desk_stream(user_query):
        if event['type'] == 'answer':
            response['answer'] = event['content']
            response['needs_email_support'] = event.get('needs_email_support', False)
        elif event['type'] == 'error':
            response['answer'] = f"Error: {event['content']}"
    return response

def summarize_conversation(history):
    """
    Summarizes the conversation history.
    """
    if not llm:
         init_clients()

    try:
        # Format history
        conversation_text = ""
        for msg in history:
            role = msg.get('role', 'User')
            content = msg.get('content', '')
            conversation_text += f"{role}: {content}\n"
            
        prompt = f"""
        Please summarize the following user inquiry and the troubleshooting steps taken so far. 
        The summary is for a Service Desk ticket.
        
        Conversation:
        {conversation_text}
        
        Summary:
        """
        
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return "Error generating summary."
