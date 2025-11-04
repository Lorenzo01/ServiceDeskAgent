# Service Desk Agentic RAG

An AI-powered Service Desk assistant designed to help users with application inquiries and troubleshooting. It uses a RAG (Retrieval-Augmented Generation) architecture with Google Gemini and local FAISS vector search to provide accurate, sourced answers.

## Features
- **Specialized Knowledge**: Expert on application functionality and troubleshooting (currently configured for Visual Studio Code).
- **RAG Architecture**: Retrieves information from indexed support tickets and documentation.
- **Streaming Responses**: Real-time feedback with a "Thinking..." process indicator.
- **Interactive Support Handoff**: Proactively offers to email the Service Desk if the query is unresolved, including an AI-generated summary.
- **Modern UI**: Cyberpunk/Glassmorphism inspired interface with dark/light mode.
- **PDF Viewer**: Integrated side-panel viewer for source documents.

## Tech Stack
- **Backend**: Python, Flask, LangChain
- **AI/Search**: Google Gemini (LLM & Embeddings), FAISS (Vector Store)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)

## How to Run
1.  Install dependencies: `pip install -r requirements.txt`
2.  Set up your environment variables:
    - Copy `.env.example` to `.env`
    - Add your `GOOGLE_API_KEY`
3.  Ingest the knowledge base: `python ingest_data.py`
4.  Run the application: `python app.py`
5.  Access at `http://localhost:8090`

## Knowledge Base
The current knowledge base is configured with a sample dataset of Visual Studio Code support tickets (`data/vscode_support_tickets.csv`). You can replace this with your own dataset by updating the CSV file and the `ingest_data.py` script.
