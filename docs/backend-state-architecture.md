# Bastion Backend State and Retrieval Architecture

## Request flow

The browser sends a stable `session_id` to FastAPI. Any FastAPI worker can
handle the request because coordination data lives outside the Python process.
Redis supplies session context, shared rate limits, locks, and reusable query
vectors. LangGraph runs the analysis, PostgreSQL records checkpoints, pgvector
retrieves specialist evidence, and PostgreSQL stores the completed report.

```text
POST /chat             -> rate limit -> session lock -> Redis messages -> Gemini
POST /analyze          -> rate limit -> analysis lock -> Redis messages -> LangGraph
LangGraph RAG node      -> query-vector cache -> fresh pgvector search per specialist
POST /documents/upload -> shared rate limit -> Amazon S3
GET /reports/{run_id}  -> PostgreSQL final_reports
```

## Redis responsibilities

- `memory.py` stores bounded messages in `bastion:session:*`. Sessions expire
  after 24 hours and retain at most 50 messages.
- `shared_state.py` implements atomic fixed-window counters in
  `bastion:ratelimit:*` and token-owned locks in `bastion:lock:*`.
- `embedding_cache.py` stores vectors in
  `bastion:query-embedding:<model>:<dimensions>:<query_hash>` for seven days by
  default. Invalid or wrong-sized entries are removed.

A query-vector cache hit skips only Gemini's query-embedding call. Market,
financial, and risk specialists still execute fresh pgvector searches during
every analysis. Retrieved chunks and agent answers are never cached in Redis.

## PostgreSQL responsibilities

LangGraph uses `checkpoints`, `checkpoint_writes`, and `checkpoint_blobs` for
durable execution state. Completed outputs use the separate `final_reports`
table, which stores the workflow and session IDs, original request, investment
memo, final report, recommendation, title, and timestamps. Both components use
the bounded connection pool in `database.py`.

## RAG and pgvector

Original PDFs remain in Amazon S3. Bastion extracts overlapping, page-aware
chunks into `documents` and `document_chunks`. Each chunk stores source metadata
and a 768-dimensional Gemini embedding. An HNSW cosine index supports nearest-
neighbor search. Each specialist builds a distinct query and receives ranked
excerpts with filename, page, URI, and similarity score.

## Main tradeoffs

- Redis enables multi-worker coordination but adds a network dependency and
  requires TTL and eviction discipline.
- Fixed-window limits are simple and atomic but can burst at window boundaries.
- Expiring locks recover after crashes, but unusually long jobs need renewal or
  a sufficiently conservative TTL.
- Query caching saves work only when specialist prompts repeat; dynamic queries
  can have a low hit rate.
- PostgreSQL is durable but slower than Redis and requires migrations and pool
  sizing.
- pgvector keeps retrieval near document metadata, while embedding-model or
  dimension changes require re-indexing.

## Verification

`backend/verify_infrastructure.py` validates Redis cross-client sessions,
counters, locks, and query-vector round trips; pgvector 0.8.2; required database
tables; three specialist ranking searches; and final-report persistence. Unit
tests additionally prove that warm query-vector cache hits do not skip any of
the three pgvector searches.
