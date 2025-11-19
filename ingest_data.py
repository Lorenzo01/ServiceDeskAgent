import os
from dotenv import load_dotenv
from langchain_community.document_loaders import CSVLoader, PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

def ingest_data():
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    
    # 1. Ingest PDF Data
    data_dir = "data"
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(data_dir, filename)
                print(f"Loading PDF data from {pdf_path}...")
                try:
                    loader = PyPDFLoader(pdf_path)
                    pdf_docs = loader.load()
                    # Split the documents into chunks
                    chunked_docs = text_splitter.split_documents(pdf_docs)
                    print(f"Loaded {len(pdf_docs)} pages from {filename}, split into {len(chunked_docs)} chunks.")
                    documents.extend(chunked_docs)
                except Exception as e:
                    print(f"Error loading PDF {filename}: {e}")

    if not documents:
        print("No documents loaded. Exiting.")
        return

    print(f"Total documents to ingest: {len(documents)}")

    print("Initializing Gemini Embeddings...")
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        return

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    print("Creating FAISS index...")
    try:
        vectorstore = FAISS.from_documents(documents, embeddings)
        print("Saving FAISS index to local folder...")
        vectorstore.save_local("faiss_index")
        print("Ingestion complete! Index saved to 'faiss_index'.")
    except Exception as e:
        print(f"Error creating/saving index: {e}")

if __name__ == "__main__":
    ingest_data()
