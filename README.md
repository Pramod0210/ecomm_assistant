# CartMate: E-Commerce Assistant

CartMate is an AI-powered assistant for e-commerce product search, review aggregation, and customer support. It leverages RAG (Retrieval-Augmented Generation) workflows, integrates with AstraDB for vector search, and provides both a FastAPI web interface and a Streamlit-based data scraper.

## Features

- **Product Review Scraper:** Scrape product details and reviews from Flipkart using Streamlit UI.
- **Vector Database Integration:** Store and retrieve product data using AstraDB vector store.
- **Agentic RAG Workflow:** Advanced conversational agent powered by LangChain and LangGraph.
- **Web Chat UI:** Interactive chatbot interface built with FastAPI and Jinja2 templates.
- **Evaluation Metrics:** Context precision and response relevancy scoring via Ragas.


## Setup

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd ecomm_assistant
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv myvenv
   source myvenv/bin/activate  # On Windows: myvenv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in your API keys (Google, Groq, AstraDB, etc.).
   - Example:
     ```
     GOOGLE_API_KEY=your-google-key
     GROQ_API_KEY=your-groq-key
     ASTRA_DB_API_ENDPOINT=...
     ASTRA_DB_APPLICATION_TOKEN=...
     ASTRA_DB_KEYSPACE=...
     ```

5. **Prepare config:**
   - Edit `prod_assistant/config/config.yaml` as needed for model and DB settings.

## Usage

### 1. Scrape Product Reviews (Streamlit UI)

```sh
streamlit run scrapper_ui.py
```
- Enter product names/descriptions and start scraping.
- Download the resulting CSV or ingest into AstraDB.

### 2. Start the Web Chatbot (FastAPI)

```sh
uvicorn prod_assistant.router.main:app --reload
```
- Visit [http://localhost:8000](http://localhost:8000) for the chat UI.

### 3. Run RAG Workflows

- **Normal RAG:**  
  See [`prod_assistant/workflow/normal_generation_workflow.py`](prod_assistant/workflow/normal_generation_workflow.py)
- **Agentic RAG:**  
  See [`prod_assistant/workflow/agentic_rag_workflow.py`](prod_assistant/workflow/agentic_rag_workflow.py)

### 4. Data Ingestion

```sh
python prod_assistant/etl/data_ingestion.py
```
- Transforms CSV data and stores it in AstraDB vector store.

## Evaluation

- Context precision and response relevancy metrics via [`prod_assistant/evaluation/ragas_eval.py`](prod_assistant/evaluation/ragas_eval.py).

## License

Proprietary. See `pyproject.toml` for details.

## Author

Pramod Kumar

---

For more details, see the source files:
- [scrapper_ui.py](scrapper_ui.py)
- [prod_assistant/router/main.py](prod_assistant/router/main.py)
- [prod_assistant/workflow/agentic_rag_workflow.py](prod_assistant/workflow/agentic_rag_workflow.py)