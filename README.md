# data-rag 📊

> Ask questions about your business data in plain language. Upload a CSV, get answers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1+-orange.svg)](https://duckdb.org)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**data-rag** is an open-source FastAPI microservice that lets you query structured business data — sales reports, inventory, financial exports — using natural language. It translates your questions into SQL via an LLM, executes them against your uploaded files using DuckDB, and returns both the answer and the query used.

It ships with a built-in web UI: an **admin panel** to upload, preview, and delete datasets, and a **chat interface** to ask questions about your data directly from the browser. No extra setup, no separate frontend project.

No data warehouse. No BI tool. No SQL skills required.

---

## Why data-rag?

Most RAG implementations are built for unstructured text. Documents, PDFs, knowledge bases. But most business data lives in spreadsheets and CSVs — and vector similarity search is a poor fit for numerical, tabular data.

**data-rag** takes a different approach: **Text-to-SQL over in-process DuckDB**.

| Problem                                      | data-rag's approach                                |
| -------------------------------------------- | -------------------------------------------------- |
| "How do I query my CSVs without a database?" | DuckDB queries CSVs natively, no import needed     |
| "Vector search doesn't understand numbers"   | SQL is the right language for tabular data         |
| "I don't want to manage a query server"      | DuckDB runs in-process, zero infrastructure        |
| "How do I know if the AI got it right?"      | Every response includes the SQL that was executed  |
| "I need this to work in my language"         | Prompt templates are fully configurable per locale |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        data-rag                         │
│                                                         │
│  POST /datasets          POST /datasets/{id}/query      │
│       │                           │                     │
│       ▼                           ▼                     │
│  ┌──────────┐            ┌────────────────┐             │
│  │  Ingest  │            │  Query Engine  │             │
│  │  Layer   │            │                │             │
│  │          │            │ 1. Build prompt │             │
│  │ - Upload │            │    w/ schema   │             │
│  │ - Schema │            │                │             │
│  │   extract│            │ 2. LLM →  SQL  │             │
│  │ - Sample │            │                │             │
│  │   rows   │            │ 3. DuckDB exec │             │
│  └────┬─────┘            │                │             │
│       │                  │ 4. LLM →       │             │
│       ▼                  │    interpretation             │
│  ┌──────────┐            └────────────────┘             │
│  │  DuckDB  │◄──────────────────┘                       │
│  │(in-proc) │                                           │
│  └──────────┘                                           │
└─────────────────────────────────────────────────────────┘
```

### Core flow

1. **Upload** a CSV → DuckDB registers it as a virtual table → schema and sample rows are extracted and stored as metadata.
2. **Ask** a question in natural language → the schema + sample rows are injected into an LLM prompt → the LLM generates a DuckDB-compatible SQL query.
3. **Execute** → DuckDB runs the SQL against the original file → results are returned as a dataframe.
4. **Interpret** → a second LLM call translates the raw result into a natural language answer, optionally flagging anomalies or suggesting follow-up questions.

---

## Features

- **Built-in web UI** — admin panel (`/panel`) + chat interface (`/`) served directly from FastAPI, no separate frontend needed
- **Zero-infrastructure analytics** — DuckDB runs in-process, no PostgreSQL or warehouse required
- **Natural language queries** — in any language your LLM supports
- **Multi-dataset support** — upload multiple files and select which dataset to query in the chat
- **Transparent SQL** — every chat response shows the SQL that was executed, so you can audit and learn
- **Schema-aware prompting** — column types, sample values, and inferred semantics are all passed to the LLM
- **Provider-agnostic** — works with Anthropic Claude, OpenAI, or any OpenAI-compatible endpoint
- **Async by default** — fully async FastAPI + async DuckDB connection pool
- **Docker-ready** — single container deployment, no external dependencies
- **Configurable prompt templates** — override system prompts per dataset or per locale

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/duendereus/data-rag.git
cd data-rag
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

```env
# .env
LLM_PROVIDER=anthropic          # anthropic | openai | openai_compatible
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://your-endpoint/v1  # for compatible providers

LLM_MODEL=claude-sonnet-4-20250514
LLM_MAX_TOKENS=2048

DUCKDB_PATH=./data/datasets.db  # set to :memory: for ephemeral
MAX_UPLOAD_SIZE_MB=50
QUERY_RESULT_LIMIT=1000         # max rows returned per query
LOG_LEVEL=INFO
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Open your browser:

- **`http://localhost:8000`** — Chat interface: select a dataset, ask questions in plain language
- **`http://localhost:8000/panel`** — Admin panel: upload, preview, and delete datasets
- **`http://localhost:8000/docs`** — Auto-generated API docs (Swagger UI)

---

## Web UI

data-rag ships with two HTML interfaces served directly from FastAPI — no build step, no separate frontend project.

### Chat (`/`)

- Select which dataset to query from a dropdown
- Type questions in plain language (any language)
- Responses include the natural language answer + the SQL that was executed
- Conversation history is maintained within the session
- "New conversation" button to reset context

### Admin panel (`/panel`)

- **Upload** CSV or Excel files via drag-and-drop or file picker
- **Preview** schema: column names, types, row count, and sample values for each dataset
- **Delete** datasets (removes file + metadata)
- Dataset list with upload timestamps and file sizes

Both interfaces use vanilla JavaScript and fetch the same REST API that's available to external integrations.

---

## API Reference

### UI routes

```http
GET /          → chat.html   (Chat interface)
GET /panel     → admin.html  (Admin panel)
```

### Upload a dataset

```http
POST /datasets
Content-Type: multipart/form-data

file: <your_file.csv>
name: "Q1 Sales 2025"          # optional, defaults to filename
description: "..."              # optional, used in LLM context
```

**Response:**

```json
{
  "id": "ds_a1b2c3",
  "name": "Q1 Sales 2025",
  "table_name": "q1_sales_2025",
  "row_count": 4820,
  "schema": [
    {
      "column": "fecha",
      "type": "DATE",
      "sample": ["2025-01-03", "2025-01-04"]
    },
    {
      "column": "producto",
      "type": "VARCHAR",
      "sample": ["Membresía Anual", "Day Pass"]
    },
    { "column": "ventas", "type": "DOUBLE", "sample": [2499.0, 350.0] },
    {
      "column": "sucursal",
      "type": "VARCHAR",
      "sample": ["CDMX", "Guadalajara"]
    }
  ],
  "created_at": "2025-03-14T10:00:00Z"
}
```

---

### Query a dataset

```http
POST /datasets/{dataset_id}/query
Content-Type: application/json

{
  "question": "¿Cuál fue la sucursal con más ventas en enero?",
  "locale": "es",
  "include_sql": true
}
```

**Response:**

```json
{
  "question": "¿Cuál fue la sucursal con más ventas en enero?",
  "answer": "La sucursal con más ventas en enero fue CDMX, con un total de $1,284,500 MXN en 847 transacciones.",
  "sql": "SELECT sucursal, SUM(ventas) AS total_ventas, COUNT(*) AS transacciones FROM q1_sales_2025 WHERE MONTH(fecha) = 1 GROUP BY sucursal ORDER BY total_ventas DESC LIMIT 1",
  "result": [
    { "sucursal": "CDMX", "total_ventas": 1284500.0, "transacciones": 847 }
  ],
  "execution_time_ms": 42,
  "dataset_id": "ds_a1b2c3"
}
```

---

### List datasets

```http
GET /datasets
```

### Get dataset info

```http
GET /datasets/{dataset_id}
```

### Delete dataset

```http
DELETE /datasets/{dataset_id}
```

### Health check

```http
GET /health
```

---

## Project Structure

```
data-rag/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, router registration
│   ├── config.py                # Settings via pydantic-settings
│   ├── dependencies.py          # DI: db session, llm client
│   │
│   ├── datasets/
│   │   ├── router.py            # /datasets endpoints
│   │   ├── service.py           # ingest logic, schema extraction
│   │   ├── repository.py        # dataset metadata persistence
│   │   └── schemas.py           # Pydantic request/response models
│   │
│   ├── query/
│   │   ├── router.py            # /datasets/{id}/query endpoint
│   │   ├── service.py           # orchestrates prompt → SQL → exec → interpret
│   │   ├── prompt_builder.py    # schema-aware prompt construction
│   │   └── schemas.py           # QueryRequest, QueryResponse
│   │
│   ├── llm/
│   │   ├── base.py              # LLMClient ABC
│   │   ├── anthropic.py         # Claude implementation
│   │   ├── openai.py            # OpenAI / compatible implementation
│   │   └── factory.py           # instantiate from config
│   │
│   ├── db/
│   │   ├── duckdb.py            # DuckDB connection management
│   │   └── metadata.py          # SQLite (or DuckDB) for dataset metadata
│   │
│   ├── templates/
│   │   ├── chat.html            # Chat interface — served at GET /
│   │   └── admin.html           # Admin panel — served at GET /panel
│   │
│   └── core/
│       ├── exceptions.py        # Custom exception classes
│       ├── logging.py           # Structured logging setup
│       └── middleware.py        # Request ID, error handling
│
├── prompts/
│   ├── sql_generation.md        # System prompt for SQL generation
│   └── interpretation.md        # System prompt for result interpretation
│
├── tests/
│   ├── fixtures/                # Sample CSVs for testing
│   ├── test_datasets.py
│   └── test_query.py
│
├── data/                        # DuckDB storage (gitignored)
├── uploads/                     # Uploaded files (gitignored)
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── pyproject.toml
└── CLAUDE.md
```

---

## Supported file formats

| Format              | Status  | Notes                    |
| ------------------- | ------- | ------------------------ |
| CSV                 | ✅ v0.1 | Auto-delimiter detection |
| TSV                 | ✅ v0.1 |                          |
| Excel (.xlsx, .xls) | ✅ v0.1 | First sheet by default   |
| Parquet             | 🔜 v0.2 |                          |
| JSON (array)        | 🔜 v0.2 |                          |

---

## Running with Docker

```bash
docker compose up
```

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    env_file: .env
```

---

## Extending data-rag

### Custom prompt templates

Override the default prompts by placing your own in the `prompts/` directory or by pointing to external files via env vars:

```env
PROMPT_SQL_GENERATION=./prompts/my_sql_prompt.md
PROMPT_INTERPRETATION=./prompts/my_interpret_prompt.md
```

Prompts receive these template variables:

- `{table_name}` — registered DuckDB table name
- `{schema}` — column names, types, and sample values
- `{question}` — user's natural language question
- `{locale}` — for multilingual responses

### Adding a new LLM provider

Implement the `LLMClient` ABC in `app/llm/base.py`:

```python
class LLMClient(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        ...
```

Then register it in `app/llm/factory.py`.

---

## Roadmap

- **v0.1** — CSV + Excel upload, natural language query, DuckDB execution, built-in chat UI + admin panel, Anthropic + OpenAI support
- **v0.2** — Multi-dataset sessions, cross-dataset JOINs, streaming responses, per-sheet Excel selection
- **v0.3** — Chart/visualization suggestions in chat, anomaly detection, scheduled queries
- **v1.0** — Multi-tenant API keys, dataset permissions, query audit log, webhook on query execution

---

## Contributing

Contributions are welcome. Please open an issue before submitting a PR for non-trivial changes.

```bash
# Setup dev environment
pip install -r requirements-dev.txt
pre-commit install

# Run tests
pytest

# Lint + format
ruff check . && ruff format .
```

---

## License

MIT — see [LICENSE](./LICENSE).

---

## Related projects

- [business-rag](https://github.com/duendereus/business-rag) — RAG microservice for unstructured business documents (policies, contracts, SOPs)

---

_Built for developers who want to give their teams a natural language interface to their own data, without vendor lock-in._
