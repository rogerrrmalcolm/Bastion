# Bastion

**A stateful, evidence-disciplined multi-agent system for M&A due diligence.**

Bastion turns buyer context, target context, transaction assumptions, and uploaded PDFs into an investment-committee package. Its typed LangGraph state machine combines specialist agents, bounded research retries, S3 document storage, embedding-based retrieval, and isolated shared state.

## Product Surface

Given structured buyer and target inputs, Bastion produces:

- A constrained execution plan with whitelisted tool assignments.
- Market analysis covering sector structure, demand, public-market proxies, and M&A implications.
- Financial analysis covering extracted metrics, QoE, liquidity, valuation support, and transaction structure.
- Acquisition-risk analysis covering severity, likelihood, diligence owners, mitigations, and agreement implications.
- An investment memo with recommendation, evidence status, conditions to proceed, open questions, and source limitations.
- A normalized report package with agent contributions and a deduplicated source register.
- Workflow diagnostics: run ID, actual execution trace, research attempts, terminal statuses, and non-fatal warnings.

The browser experience adds buyer/target intake, PDF upload, a Three.js workflow visualization, structured report rendering, and a local deal-summary dashboard.

## System Architecture

```mermaid
flowchart TB
    subgraph Browser["Vite + Three.js client"]
        Intake["Buyer / target / deal intake"]
        UI["Workflow visualization + report UI"]
        LocalDash[("LocalStorage dashboard")]
        Intake --> UI
        UI <--> LocalDash
    end

    subgraph API["FastAPI application"]
        Routes["Typed HTTP routes"]
        Upload["Server-side PDF upload"]
        Session["Redis-backed session context"]
        Graph["Compiled LangGraph runtime"]
        Routes --> Session
        Routes --> Graph
        Routes --> Upload
    end

    subgraph Runtime["Diligence runtime"]
        Documents["PDF extraction + Gemini embeddings"]
        Research["Deterministic research functions"]
        Agents["Structured Gemini agents"]
        Report["Deterministic report assembly"]
        Research --> Agents --> Report
    end

    UI -->|"POST /analyze"| Routes
    Intake -->|"multipart PDF"| Upload
    Graph <--> Runtime
    Session <--> Memory[("Redis shared sessions")]
    Routes <--> RedisControl[("Redis sessions + controls + query vectors")]
    Graph <--> State["Per-run BastionGraphState"]
    Graph <--> Checkpoints[("PostgreSQL checkpoints")]
    Upload --> S3[("Amazon S3")]
    S3 --> Documents --> Vectors[("Supabase pgvector")]
    Vectors --> State
    Research --> PublicData["Market data + news endpoints"]
    Agents --> Gemini["Gemini 2.5 Flash on Vertex AI"]
```

## Stateful Multi-Agent Graph

LangGraph is **stateful**, not stateless. The topology is compiled once, but each invocation receives an isolated `BastionGraphState`. Nodes read the current state and return partial updates; LangGraph merges those updates before routing to the next node.

Not every node is an agent. Bastion deliberately separates model-backed judgment from deterministic retrieval and report construction.

```mermaid
flowchart LR
    START((START)) --> O["Orchestrator agent"]
    O --> DR["Document embedding retrieval"]
    DR --> MR["Market research"]
    MR -->|"transient failure; attempts remain"| MR
    MR -->|"success or exhausted"| M["Market agent"]
    M --> FR["Financial research"]
    FR -->|"transient failure; attempts remain"| FR
    FR -->|"success or exhausted"| F["Financial agent"]
    F --> RR["Risk research"]
    RR -->|"transient failure; attempts remain"| RR
    RR -->|"success or exhausted"| R["Risk agent"]
    R --> MM["Memo agent"]
    MM --> BR["Build report"]
    BR --> END((END))
```

The core workstream is sequential by design:

1. Market conditions establish the demand, competition, timing, and valuation backdrop.
2. Financial analysis consumes the market view before assessing QoE, liquidity, leverage, and structure.
3. Risk analysis consumes both upstream outputs before mapping closing and integration exposure.
4. Memo synthesis consumes all specialist outputs before making a recommendation.

Parallelizing those agents would reduce wall-clock time but weaken the information dependencies the product is intended to preserve. Bastion instead parallelizes independent I/O *inside* research nodes with bounded thread pools.

## State Ownership and Memory

The graph state is the shared working record for one invocation:

```mermaid
flowchart LR
    Request["Analyze request"] --> State0["Initial BastionGraphState"]
    State0 --> O["orchestrator writes orchestration_plan"]
    O --> Docs["retrieval writes agent-specific document_contexts"]
    O --> M["market writes market_analysis"]
    M --> F["financial reads market + writes financial_analysis"]
    F --> R["risk reads market + financial + writes risk_analysis"]
    R --> Memo["memo reads all specialists + writes investment_memo"]
    Memo --> Report["deterministic report update"]

    SessionID["session_id"] --> Memory["bounded Redis conversation memory"]
    Memory --> State0
```

| Mechanism | Scope | Purpose | Current implementation |
| --- | --- | --- | --- |
| `BastionGraphState` | One analysis run | Typed working record shared by graph nodes | LangGraph `TypedDict` with reducers |
| Embedding retrieval | Across analysis runs | Persist page-aware S3 chunks and select excerpts per specialist | Gemini 768-dimensional embeddings + Supabase pgvector HNSW search |
| Partial node update | One superstep | Add or replace fields without mutating global state | Dictionary returned by each node |
| Session memory | Configurable Redis TTL | Bounded continuity shared by every API worker using the same `session_id` | Redis lists with message caps and expiry |
| Rate limiting | Configurable fixed window | Enforce shared request counts across all API workers | Atomic Redis `INCR`/`EXPIRE` script keyed by route and client |
| Distributed locks | Per active session operation | Prevent concurrent workers from processing the same session operation | Token-owned Redis `SET NX EX` locks with compare-and-delete release |
| Query-embedding cache | Seven-day default TTL | Avoid repeated Gemini query-vector calls without caching retrieval results | Redis value keyed by embedding model, dimensions, and normalized-query SHA-256 |
| Checkpointer | Across restarts | Durable graph snapshots for recovery, replay, and inspection | PostgreSQL `PostgresSaver` |
| Final report store | Across restarts | Retain completed request, memo, and report payloads | PostgreSQL `final_reports`, keyed by `workflow_run_id` |
| LangGraph Store | Across workflows | Searchable long-term memory | Not implemented |

Redis is visible at the API boundary rather than inside agent business logic:

```text
POST /chat             -> rate limit -> session lock -> session messages -> Gemini
POST /analyze          -> rate limit -> analysis lock -> session messages -> LangGraph
LangGraph RAG node      -> query-vector cache -> fresh pgvector search per specialist
POST /documents/upload -> shared rate limit -> Amazon S3
```

The corresponding Redis key families are `bastion:session:*`,
`bastion:ratelimit:*`, `bastion:lock:*`, and `bastion:query-embedding:*`.
Session and coordination state are replaceable; PostgreSQL remains the durable
source for checkpoints and completed reports.

Every `/analyze` request generates a new `workflow_run_id` for correlation, while the graph invocation starts from a newly constructed state object. Tests invoke the same compiled graph repeatedly and verify that company context and run IDs do not leak between deals. Conversation memory is loaded separately, truncated to bounded character budgets, and cannot replace the current structured deal context.

Each analysis uses its unique `workflow_run_id` as the LangGraph checkpoint thread, preventing separate analyses in the same user session from merging state. Conversation continuity remains independently keyed by `session_id` in Redis.

## Reliability Model

Bastion uses separate failure policies for separate failure domains:

- **Research retrieval:** each research node has a conditional self-edge and at most three attempts.
- **Cycle safety:** LangGraph also receives a recursion limit of 32 as a second termination guard.
- **Evidence failure:** after retry exhaustion, the specialist receives a machine-readable limitation packet and continues only from supplied context.
- **Model transport:** Gemini retries HTTP `429` and transient `5xx` responses plus transport failures with exponential backoff.
- **Planning failure:** a failed orchestrator falls back to a validated, dependency-preserving default plan and emits a warning.
- **Output integrity:** Gemini responses are validated directly against Pydantic JSON schemas; the final report is assembled deterministically.

Two append-only reducer fields, `execution_trace` and `workflow_warnings`, make retries and fallbacks observable rather than silently overwriting prior events.

## Evidence Discipline

The schema forces findings to distinguish source-backed evidence, tool results, analyst inference, user assumptions, and unresolved diligence. Live research packets carry URLs, publishers, retrieval dates, errors, and deal relevance where available. If evidence is absent, the output records the missing item and its decision impact instead of manufacturing a metric, multiple, citation, or risk.

Current research functions include:

- Page-aware PDF extraction and embedding retrieval from private S3 uploads.
- Yahoo Finance chart data for detected tickers and public-market proxies.
- Google News RSS searches for sector, transaction, regulatory, cyber, and competitive signals.
- Deterministic extraction of financial and risk signals from supplied text.
- Derived runway calculations when both cash and burn inputs are present.

## Performance Engineering

The benchmark harness runs the ten-node success path with synthetic agent/research outputs, measuring local orchestration and state overhead rather than Gemini, embedding, S3, or internet latency.

| Local operation, 100 runs | p50 | p95 |
| --- | ---: | ---: |
| Ten-node state graph | 1.896 ms | 2.746 ms |

Environment: Python 3.13.13 on Windows 11. The 100-run baseline demonstrates that local graph routing is small compared with the external model and research calls intentionally excluded from the harness. The historical process-local memory measurements were removed after session storage moved to Redis; Redis latency must be re-baselined against the selected deployment. See [`docs/performance-baseline.json`](docs/performance-baseline.json) for the original result and machine metadata.

### Token-efficiency baseline

LangGraph does not reduce tokens by itself. Bastion reduces context growth by using graph state as a typed working record and projecting only the plan step and upstream outputs required by the next agent. The benchmark compares that implementation with a counterfactual stateless chat that must replay its complete prior user/assistant transcript on every downstream call.

| Agent input | Selective shared state | Transcript replay | Estimated reduction |
| --- | ---: | ---: | ---: |
| Orchestrator | 1,601 | 1,601 | 0.00% |
| Market | 4,472 | 7,004 | 36.15% |
| Financial | 4,970 | 9,676 | 48.64% |
| Risk | 6,319 | 13,648 | 53.70% |
| Memo | 4,961 | 14,834 | 66.56% |
| **Five-call total** | **22,323** | **46,763** | **52.26%** |

The fixed `synthetic-buyer-target-v1` fixture therefore uses an estimated **24,440 fewer input tokens**, with the advantage increasing downstream as transcript history accumulates. Both scenarios keep the same five calls, Gemini 2.5 Flash target, system instruction, response schemas, company context, research packets, and fixed outputs.

These planning estimates use `ceil(UTF-8 request bytes / 4)` and include system instructions and response schemas. They exclude actual tokenization, outputs, retries, and live research. See [`docs/token-efficiency-baseline.json`](docs/token-efficiency-baseline.json); the harness can also call Vertex AI `countTokens`.

The production frontend build separates Bastion's 40.72 kB application chunk (13.29 kB gzip) from the 519.16 kB Three.js vendor chunk (129.80 kB gzip). That keeps application deployments small and allows browsers/CDNs to cache the rendering engine independently.

Performance decisions already represented in the code:

- Redis stores bounded, expiring session messages outside Python process memory.
- Redis atomically counts rate limits and coordinates short-lived session locks across FastAPI workers.
- Redis caches query embeddings but never chunk matches or agent retrieval results; pgvector retrieval runs for every specialist on every analysis.
- PostgreSQL persists LangGraph checkpoints through a bounded connection pool so workflow state survives backend restarts.
- Independent quote/news fetches run concurrently while dependency-heavy agents remain sequential.
- Typed state projects only required upstream outputs into each agent instead of replaying the complete workflow transcript.
- Agent handoff payloads and session context have explicit character bounds to control token growth.
- Vertex client creation is deferred until the first model operation, so local graph inspection and prompt-only tests do not resolve cloud credentials.
- Network calls use finite timeouts and result caps.
- Deterministic calculation and report nodes avoid unnecessary model calls.
- Rolldown vendor grouping isolates Three.js from frequently changing application code.

Reproduce the baseline:

```powershell
.\.venv\Scripts\python.exe backend\benchmarks\benchmark_orchestration.py --iterations 100
.\.venv\Scripts\python.exe backend\benchmarks\benchmark_token_efficiency.py --counter estimate --output docs\token-efficiency-baseline.json
# Exact Gemini counts; sends the synthetic fixture to the configured Vertex project.
.\.venv\Scripts\python.exe backend\benchmarks\benchmark_token_efficiency.py --counter gemini
```

## API

| Method | Route | Responsibility |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `POST` | `/analyze` | Run the typed diligence graph |
| `POST` | `/chat` | Session-aware diligence chat |
| `POST` | `/documents/upload` | Validate and upload a PDF through the backend to S3 |
| `GET` | `/sessions/{session_id}/memory` | Inspect Redis-backed conversation messages |
| `GET` | `/reports/{workflow_run_id}` | Read a completed report persisted in PostgreSQL |
| `GET` | `/workflow/graph` | Inspect the runtime node/edge manifest |

FastAPI also exposes generated OpenAPI documentation at `/docs` when the backend is running.

## Stack

- **Backend:** Python, FastAPI, Pydantic, LangGraph
- **Reasoning:** Google Gemini 2.5 Flash through Vertex AI
- **State:** typed per-run LangGraph state, Supabase PostgreSQL checkpoints, Redis session memory, pgvector
- **Evaluation:** DeepEval
- **Research:** S3 PDF extraction, Gemini embeddings, deterministic tools, Yahoo Finance, Google News RSS
- **Object storage:** Amazon S3 via Boto3
- **Frontend:** Vite, vanilla JavaScript, Three.js

## Repository Map

```text
Bastion/
|-- backend/
|   |-- agents/              # Agent prompts and LangGraph orchestration
|   |-- benchmarks/          # Reproducible local performance harness
|   |-- tests/               # Topology, retry, state-isolation, memory, API tests
|   |-- tools/               # Market, financial, and risk research functions
|   |-- main.py              # FastAPI routes
|   |-- memory.py            # Bounded Redis session store
|   |-- shared_state.py      # Redis rate-limit counters and distributed locks
|   |-- embedding_cache.py   # Redis query-vector cache; no retrieval-result caching
|   |-- database.py          # Shared bounded PostgreSQL connection pool
|   |-- checkpointing.py     # Pooled PostgreSQL LangGraph checkpointer
|   |-- report_store.py      # Completed report persistence and retrieval
|   |-- document_store.py    # Supabase document and pgvector persistence
|   |-- document_retrieval.py # PDF chunking, embedding, and ranking
|   |-- verify_infrastructure.py # Live Redis/Postgres/vector health checks
|   |-- report_service.py    # Deterministic report normalization
|   `-- schemas.py           # Cross-agent and API contracts
|-- docs/
|   |-- langgraph-workflow.md
|   `-- performance-baseline.json
|-- scripts/                 # Local infrastructure setup
|-- supabase/                # CLI config, migrations, and seed data
|-- compose.yaml             # Persistent Redis development service
`-- frontend/                # Vite + Three.js client
```

## Run Locally

Requirements: Python 3.10+, Node.js 22.12+, and Docker Desktop using Linux containers.

```powershell
git clone https://github.com/rogerrrmalcolm/Bastion.git
cd Bastion
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
npm install
Copy-Item .env.example .env
```

Configure the Google/Vertex and S3 values in `.env`. Then download, start, configure, migrate, and verify Redis plus the local Supabase stack:

```powershell
.\scripts\start-local-services.ps1
```

The script starts persistent Redis from `compose.yaml`, starts Supabase, applies migrations, writes generated local endpoints and keys to the gitignored `.env.services.local`, creates LangGraph checkpoint tables, and runs a live Redis/Data API/pgvector round trip.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload
```

Supabase Studio is available at [http://127.0.0.1:54323](http://127.0.0.1:54323), and Redis Insight is available at [http://127.0.0.1:5540](http://127.0.0.1:5540). Redis Insight is preconfigured for the Docker-internal endpoint `redis:6379`; the backend uses the host endpoint `redis://127.0.0.1:6379/0`. PostgreSQL and LangGraph use `postgresql://postgres:postgres@127.0.0.1:54322/postgres`. To stop the services without deleting their volumes:

```powershell
docker compose stop redis redisinsight
npx supabase stop
```

For a hosted Supabase project, run `npx supabase login`, `npx supabase link --project-ref <project-ref>`, and `npx supabase db push`. Configure `DATABASE_URL` with the hosted project's direct or session-pooler PostgreSQL connection string and keep the service-role key server-side only.

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

For a deployed frontend, create `frontend/.env.local` with:

```env
VITE_API_BASE_URL=https://your-backend.example.com
```

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `GOOGLE_GENAI_USE_VERTEXAI` | Yes | Set `true` for Vertex AI |
| `GOOGLE_CLOUD_PROJECT` | Yes | Google Cloud project ID |
| `GOOGLE_CLOUD_LOCATION` | Yes | Vertex AI region |
| `GEMINI_EMBEDDING_MODEL` | No | Defaults to `gemini-embedding-001` |
| `GEMINI_EMBEDDING_DIMENSIONS` | No | Fixed at 768 to match the pgvector schema |
| `GOOGLE_APPLICATION_CREDENTIALS` | Deployment-dependent | Service-account file path; use workload identity in production where possible |
| `S3_BUCKET` | For PDF upload | Destination bucket |
| `AWS_REGION` | For PDF upload | Bucket region |
| `S3_PREFIX` | No | Object-key prefix; defaults to `pdfs` |
| `CORS_ORIGINS` | No | Comma-separated allowed frontend origins |
| `REDIS_URL` | Yes | Shared Redis connection for sessions, rate-limit counters, and distributed locks |
| `SESSION_TTL_SECONDS` | No | Session expiry; defaults to 86,400 seconds |
| `SESSION_MAX_MESSAGES` | No | Maximum stored messages per session; defaults to 50 |
| `RATE_LIMIT_WINDOW_SECONDS` | No | Shared fixed-window duration; defaults to 60 seconds |
| `CHAT_RATE_LIMIT` | No | `/chat` requests allowed per client/window; defaults to 30 |
| `ANALYZE_RATE_LIMIT` | No | `/analyze` requests allowed per client/window; defaults to 10 |
| `UPLOAD_RATE_LIMIT` | No | `/documents/upload` requests allowed per client/window; defaults to 10 |
| `CHAT_LOCK_TTL_SECONDS` | No | Maximum lifetime for a session chat lock; defaults to 120 seconds |
| `ANALYZE_LOCK_TTL_SECONDS` | No | Maximum lifetime for a session analysis lock; defaults to 1,800 seconds |
| `QUERY_EMBEDDING_CACHE_TTL_SECONDS` | No | Query-vector cache TTL; defaults to 604,800 seconds |
| `DATABASE_URL` | Yes | PostgreSQL connection for durable LangGraph checkpoints |
| `POSTGRES_POOL_MIN_SIZE` | No | Minimum checkpoint connection-pool size |
| `POSTGRES_POOL_MAX_SIZE` | No | Maximum checkpoint connection-pool size |
| `LANGGRAPH_STRICT_MSGPACK` | Yes | Restricts checkpoint deserialization to safe types |
| `SUPABASE_URL` | Yes | Supabase Data API endpoint |
| `SUPABASE_ANON_KEY` | Frontend only | Publishable browser key; never substitutes for server authorization |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only | Secret server key for document persistence and vector RPC access |

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe -m compileall backend
.\.venv\Scripts\python.exe backend\verify_infrastructure.py
cd frontend
npm run build
```

Tests cover agent order, embedding ranking and handoffs, fresh pgvector searches on cache hits, retries, graph parity, run/session isolation, Redis controls, report persistence, context bounds, and API behavior.

## Current Boundaries

- PDF files stay in S3; extracted chunks and 768-dimensional embeddings persist in Supabase and are reused by source URI. Scanned PDFs still require OCR, and deal-level authorization is not wired yet.
- Session history requires reachable Redis, and durable graph execution requires reachable PostgreSQL; startup configuration should use managed secrets.
- Checkpoints are durable and isolated by workflow run, but the API does not yet expose pause/resume or replay controls.
- Completed report packages are stored separately in `final_reports` and are readable by workflow run ID.
- Authentication and tenant authorization are not implemented. The backend uses the Supabase secret key, so its document tables are inaccessible to anonymous and authenticated Data API roles until explicit RLS policies are designed.
- The frontend dashboard stores summaries in browser `localStorage`; it is not a shared team pipeline.
- S3 access is server-side, but bucket privacy, encryption, lifecycle, IAM, malware scanning, and document deletion remain deployment responsibilities.

## License

MIT
