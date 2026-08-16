# CartMate — Agentic E-Commerce Assistant (RAG + MCP)

A conversational product assistant that answers shopping questions from real scraped reviews rather than model priors. Questions about price, ratings, or opinions are routed to a LangGraph agent that retrieves from a vector store of Flipkart product reviews, **grades its own retrieved context**, and falls back to live web search when that context turns out to be weak.

Retrieval and web search are not hardcoded into the graph — they are exposed as **MCP tools** by a standalone server, so the agent discovers its capabilities at runtime instead of importing them.

The same codebase runs as a local FastAPI app or as a containerized deployment on EKS, provisioned by CloudFormation and shipped by GitHub Actions.

---

## Why this project

The interesting problem in retrieval isn't fetching documents — it's knowing when the documents you fetched are not good enough to answer with.

- **The agent grades its own context.** After retrieval, a grader node judges whether the documents actually address the question. Irrelevant context doesn't get passed to the generator and dressed up as an answer.
- **A bad retrieval becomes a better query.** On a `no` verdict the graph doesn't give up — a rewriter node reformulates the question for search, then web search runs against the improved query. Failure is a branch in the graph, not an exception.
- **Two-stage retrieval, not top-k.** MMR search fetches 20 candidates and keeps 4 diverse ones, then an `LLMChainFilter` drops chunks the LLM judges irrelevant. Diversity first, precision second.
- **Tools live behind MCP.** The retriever and DuckDuckGo search are published by an MCP server over stdio. The agent enumerates tools at startup, so a new capability is a new server-side tool — not a graph edit.
- **The provider is a config decision.** Google, Groq, and OpenAI blocks all live in `config.yaml`; `LLM_PROVIDER` picks one at load time. No client code changes to switch models.
- **Quality is measured.** A RAGAS harness scores context precision and response relevancy against the live retrieve-and-generate path.

---

## Architecture

```
┌──────────────┐                    ┌──────────────┐
│  Streamlit   │                    │   Chat UI    │
│  Scraper UI  │                    │   (Jinja2)   │
└──────┬───────┘                    └──────┬───────┘
       │ scrape → CSV                      │ POST /get
       ▼                                   ▼
┌──────────────┐                    ┌──────────────┐
│  Ingestion   │                    │   FastAPI    │
│   pipeline   │                    │   backend    │
└──────┬───────┘                    └──────┬───────┘
       │ embed + upsert                    │
       │                                   ▼
       │                            ┌──────────────┐
       │                            │  LangGraph   │
       │                            │ agentic RAG  │
       │                            └──────┬───────┘
       │                                   │ stdio
       │                                   ▼
       │                            ┌──────────────┐
       │                            │  MCP server  │
       │                            │hybrid_search │
       │                            └───┬──────┬───┘
       ▼                                ▼      ▼
┌────────────────────────────────────────┐ ┌────────────┐
│         AstraDB vector store           │ │ DuckDuckGo │
└────────────────────────────────────────┘ └────────────┘
```

### The agent graph

Defined in [`agentic_workflow_with_mcp_websearch.py`](prod_assistant/workflow/agentic_workflow_with_mcp_websearch.py):

```
                     ┌─────────────┐
   question  ───────▶│  Assistant  │──── no product intent ───▶ END
                     └──────┬──────┘
                            │ product intent
                            ▼
                     ┌─────────────┐
                     │  Retriever  │   MCP tool: get_product_info
                     └──────┬──────┘
                            ▼
                     ┌─────────────┐
                     │   Grader    │   are these docs relevant?
                     └──┬───────┬──┘
                    yes │       │ no
                        │       ▼
                        │  ┌──────────┐     ┌───────────┐
                        │  │ Rewriter │────▶│ WebSearch │  MCP tool: web_search
                        │  └──────────┘     └─────┬─────┘
                        ▼                         │
                     ┌─────────────┐◀─────────────┘
                     │  Generator  │
                     └──────┬──────┘
                            ▼
                           END
```

`MemorySaver` checkpoints state per `thread_id`, so the graph is resumable across turns.

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Agent orchestration | LangGraph | Grading and retry are graph edges, not `if` statements |
| Tool transport | MCP (`FastMCP` + `langchain-mcp-adapters`) | Tools are discovered at runtime, decoupled from the agent |
| Vector store | AstraDB | Serverless vectors with namespace isolation, no cluster to run |
| Embeddings | Google `text-embedding-004` | Strong retrieval quality on short review text |
| LLM | Google / Groq / OpenAI | Selected by `LLM_PROVIDER`; all three configured in `config.yaml` |
| Retrieval | MMR + `LLMChainFilter` | Diverse candidates, then LLM-judged precision filtering |
| Web fallback | DuckDuckGo (`ddgs`) | No API key required for the fallback path |
| API | FastAPI + Jinja2 | Async-native, serves both the JSON path and the chat UI |
| Scraping | Selenium + `undetected-chromedriver` | Flipkart renders reviews client-side and fingerprints bots |
| Scraper UI | Streamlit | Search, scrape, preview, and ingest in one surface |
| Evaluation | RAGAS | Context precision + response relevancy |
| Logging | structlog | JSON lines to console and a timestamped file |
| Deployment | Docker → ECR → EKS | GitHub Actions build/push/rollout, CloudFormation for infra |

---

## Retrieval strategy

Review text is short, repetitive, and highly redundant — ten reviews of the same phone say the same three things. Plain top-k similarity returns ten near-duplicates and wastes the context window. [`retrieval.py`](prod_assistant/retriever/retrieval.py) instead runs two stages:

1. **MMR search** — `fetch_k=20` candidates reduced to `k=4` with `lambda_mult=0.7`, trading a little relevance for coverage of *distinct* opinions, with a `score_threshold` of `0.6`.
2. **Contextual compression** — an `LLMChainFilter` reviews each surviving chunk and drops the ones that don't bear on the question.

Each chunk keeps `product_id`, `product_title`, `rating`, `total_reviews`, and `price` as metadata, so the generator can cite a concrete price and rating instead of paraphrasing review prose.

---

## MCP tools

[`product_search_server.py`](prod_assistant/mcp_servers/product_search_server.py) runs a `FastMCP` server named `hybrid_search` over stdio:

| Tool | Purpose |
|---|---|
| `get_product_info(query)` | Retrieve product context from the AstraDB vector store |
| `web_search(query)` | DuckDuckGo search, used when local context is graded irrelevant |

Both return formatted strings and convert exceptions into readable messages, so a tool failure degrades the answer instead of killing the graph run.

---

## Configuration

Copy [`.env.example`](.env.example) to `.env` and fill it in:

```bash
cp .env.example .env
```

`GOOGLE_API_KEY` is always required (embeddings are Google regardless of the chat provider). The AstraDB trio is validated at startup in both the retriever and the ingestion pipeline — the app fails immediately with the missing variable named, rather than at first query with a connection error.

Model and retrieval settings live in [`config.yaml`](prod_assistant/config/config.yaml) — collection name, embedding model, `top_k`, and one block per LLM provider.

---

## Running it

```bash
python -m venv myvenv
source myvenv/bin/activate        # Windows: myvenv\Scripts\activate
pip install -r requirements.txt
```

### 1. Scrape reviews

```bash
streamlit run scrapper_ui.py
```

Enter product names, choose how many products and reviews per search, and scrape. Results are written to `data/product_reviews.csv` and can be downloaded or pushed straight into AstraDB from the same screen.

Requires a local Chrome install — `undetected-chromedriver` downloads a matching driver.

### 2. Ingest into the vector store

From the Streamlit UI, or directly:

```bash
python prod_assistant/etl/data_ingestion.py
```

Reads `data/product_reviews.csv`, builds one `Document` per product (reviews as content, product attributes as metadata), embeds, and upserts into AstraDB.

### 3. Start the assistant

```bash
uvicorn prod_assistant.router.main:app --reload
```

Chat UI at [http://localhost:8000](http://localhost:8000). The MCP server is spawned automatically as a stdio subprocess by the agent.

### Evaluation

```bash
python prod_assistant/evaluation/ragas_eval.py
```

Scores context precision and response relevancy via RAGAS. This calls the LLM API and costs tokens.

---

## Run with Docker

```bash
docker build -t cartmate .
docker run -p 8000:8000 --env-file .env cartmate
```

---

## Deployment

`.github/workflows/infra.yaml` provisions the infrastructure from [`eks-with-ecr.yaml`](infra/eks-with-ecr.yaml) — a VPC, an EKS cluster, a `t3.medium` node group, and an ECR repository.

`.github/workflows/deploy.yaml` then runs on every push to `main`:

1. Verify the EKS cluster exists, fail fast if `infra` hasn't been run
2. Build and push the image to ECR, tagged with a build timestamp and `latest`
3. Sync API keys into the `product-assistant-secrets` Kubernetes secret
4. Apply [`deployment.yaml`](k8/deployment.yaml) (2 replicas) and [`service.yaml`](k8/service.yaml) (LoadBalancer, `80 → 8000`)
5. Patch the deployment to the new tag and verify the rollout — dumping pod logs and failing the job if it stalls

Secrets are injected as environment variables from `secretKeyRef`; none are baked into the image.

---

## Repository layout

```
prod_assistant/
├── router/main.py            FastAPI app, chat endpoint, static + templates
├── workflow/                 LangGraph pipelines
│   ├── agentic_workflow_with_mcp_websearch.py   retrieval + grading + web fallback
│   ├── agentic_workflow_with_mcp.py             retrieval via MCP only
│   ├── agentic_rag_workflow.py                  direct retriever, no MCP
│   └── normal_generation_workflow.py            baseline RAG, no agent
├── mcp_servers/              FastMCP server (retriever + web search) and a test client
├── retriever/retrieval.py    MMR + contextual compression over AstraDB
├── etl/                      Flipkart scraper, CSV → AstraDB ingestion
├── evaluation/ragas_eval.py  context precision + response relevancy
├── prompt_library/           versioned prompt registry with placeholder validation
├── utils/                    config loader, model/provider loader
├── logger/ · exception/      structlog JSON logging, custom exception with frame walk
└── config/config.yaml        models, providers, retriever settings
scrapper_ui.py                Streamlit scraping + ingestion UI
templates/ · static/          chat interface
infra/ · k8/ · .github/       CloudFormation, manifests, CI/CD
```

The four workflow variants are deliberate: they trace the progression from baseline RAG to a graph that grades itself, and finally to one whose tools arrive over MCP.

---

## Known limitations

Honest notes on where this stops short of production:

- **Intent routing is keyword-based.** [`_ai_assistant`](prod_assistant/workflow/agentic_workflow_with_mcp_websearch.py) checks whether the message contains `"price"`, `"review"`, or `"product"` to decide whether to retrieve. "How much is the S25?" never reaches the retriever. LLM tool-calling is the fix.
- **The agent is rebuilt per request.** [`main.py`](prod_assistant/router/main.py) constructs `AgenticRAG()` inside the request handler, so every message recompiles the graph and respawns the MCP subprocess. Because `MemorySaver` is per-instance and `thread_id` is hardcoded to `"default_thread"`, conversation history does not survive between turns despite the checkpointer being wired in.
- **No test suite.** `test/` contains only `__init__.py`.
- **The scraper is tied to Flipkart's markup.** Review extraction selects on obfuscated class names (`div._27M-vq`, `div.col.EPCmJX`) that change without notice.
- **Evaluation failures are silent.** The RAGAS helpers `return e` on exception rather than raising, so a failed metric surfaces as a score-shaped object.
- **Packaging is nominal.** `pyproject.toml` sets `include = ["ecomm_assistant*"]`, which matches nothing under `prod_assistant/`; imports resolve through the editable install's path entry rather than an installed package.

---

## License

MIT — see [LICENSE](LICENSE).
