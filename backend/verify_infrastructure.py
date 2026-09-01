from __future__ import annotations

import os
from uuid import uuid4

import psycopg
from redis import Redis

import configuration  # noqa: F401
from document_store import SupabaseDocumentStore
from embedding_cache import RedisQueryEmbeddingCache
from memory import RedisSessionStore
from shared_state import DistributedLockUnavailable, RedisSharedState


def main() -> None:
    redis_client = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    print(f"Redis ping: {redis_client.ping()}")

    shared_id = f"health-{uuid4()}"
    state_one = RedisSharedState(client=redis_client)
    state_two = RedisSharedState(
        client=Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    )
    session_one = RedisSessionStore(client=redis_client, ttl_seconds=60)
    session_two = RedisSessionStore(
        client=Redis.from_url(os.environ["REDIS_URL"], decode_responses=True),
        ttl_seconds=60,
    )
    try:
        results = [
            state_one.check_rate_limit(
                "health", shared_id, limit=2, window_seconds=60
            ),
            state_two.check_rate_limit(
                "health", shared_id, limit=2, window_seconds=60
            ),
            state_one.check_rate_limit(
                "health", shared_id, limit=2, window_seconds=60
            ),
        ]
        if [result.allowed for result in results] != [True, True, False]:
            raise RuntimeError("Redis shared rate-limit counter failed.")

        second_worker_blocked = False
        with state_one.lock("health", shared_id, ttl_seconds=60):
            try:
                with state_two.lock("health", shared_id, ttl_seconds=60):
                    pass
            except DistributedLockUnavailable:
                second_worker_blocked = True
        if not second_worker_blocked:
            raise RuntimeError("Redis distributed lock did not exclude another worker.")

        session_one.add_message(shared_id, "user", "shared worker health check")
        if session_two.list_messages(shared_id)[0].content != "shared worker health check":
            raise RuntimeError("Redis session messages were not shared across clients.")

        embedding_cache = RedisQueryEmbeddingCache(
            client=redis_client,
            ttl_seconds=60,
        )
        cache_vector = [1.0, *([0.0] * 767)]
        embedding_cache.set(shared_id, cache_vector)
        if embedding_cache.get(shared_id) != cache_vector:
            raise RuntimeError("Redis query-embedding cache failed its round trip.")
    finally:
        redis_client.delete(
            f"bastion:ratelimit:health:{shared_id}",
            f"bastion:lock:health:{shared_id}",
            f"bastion:session:{shared_id}:metadata",
            f"bastion:session:{shared_id}:messages",
            RedisQueryEmbeddingCache.key_for(shared_id),
        )

    print("Redis cross-worker counters, locks, and sessions: ready")

    store = SupabaseDocumentStore()
    store.get_document_statuses(["s3://bastion/health-check.pdf"])
    print("Supabase Data API: reachable")

    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        vector_version = connection.execute(
            "select extversion from pg_extension where extname = 'vector'"
        ).fetchone()
        table_names = {
            row[0]
            for row in connection.execute(
                """
                select tablename
                from pg_tables
                where schemaname = 'public'
                  and tablename in (
                    'documents',
                    'document_chunks',
                    'checkpoints',
                    'checkpoint_writes',
                    'checkpoint_blobs',
                    'final_reports'
                  )
                """
            )
        }

    required_tables = {
        "documents",
        "document_chunks",
        "checkpoints",
        "checkpoint_writes",
        "checkpoint_blobs",
        "final_reports",
    }
    missing_tables = required_tables - table_names
    if not vector_version:
        raise RuntimeError("The pgvector extension is not installed.")
    if missing_tables:
        raise RuntimeError(
            f"Missing persistence tables: {', '.join(sorted(missing_tables))}"
        )

    health_uri = f"s3://bastion/health-check-{uuid4()}.pdf"
    market_vector = [1.0, 0.0, 0.0, *([0.0] * 765)]
    financial_vector = [0.0, 1.0, 0.0, *([0.0] * 765)]
    risk_vector = [0.0, 0.0, 1.0, *([0.0] * 765)]
    try:
        store.replace_document_chunks(
            source_uri=health_uri,
            filename="health-check.pdf",
            page_count=3,
            chunks=[
                {
                    "page": 1,
                    "chunk_index": 0,
                    "content": "Market demand and competitive growth evidence.",
                    "embedding": market_vector,
                },
                {
                    "page": 2,
                    "chunk_index": 0,
                    "content": "Revenue, EBITDA margin, and cash-flow evidence.",
                    "embedding": financial_vector,
                },
                {
                    "page": 3,
                    "chunk_index": 0,
                    "content": "Regulatory, cybersecurity, and integration risks.",
                    "embedding": risk_vector,
                },
            ],
            embedding_model="health-check",
            embedding_dimensions=768,
        )
        expected_pages = [(market_vector, 1), (financial_vector, 2), (risk_vector, 3)]
        for query_vector, expected_page in expected_pages:
            matches = store.match_chunks(
                query_embedding=query_vector,
                source_uris=[health_uri],
                match_count=3,
            )
            if not matches or matches[0]["page"] != expected_page:
                raise RuntimeError(
                    "The pgvector specialist ranking check returned the wrong chunk."
                )

        report_run_id = str(uuid4())
        with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
            connection.execute(
                """
                insert into public.final_reports (
                    workflow_run_id, session_id, title, recommendation,
                    request_payload, investment_memo, report_payload
                ) values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    report_run_id,
                    shared_id,
                    "Infrastructure health check",
                    "proceed",
                    "{}",
                    "{}",
                    "{}",
                ),
            )
            persisted = connection.execute(
                "select workflow_run_id from public.final_reports where workflow_run_id = %s",
                (report_run_id,),
            ).fetchone()
            if not persisted:
                raise RuntimeError("Final report persistence failed its round trip.")
            connection.execute(
                "delete from public.final_reports where workflow_run_id = %s",
                (report_run_id,),
            )
    finally:
        with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
            connection.execute(
                "delete from public.documents where source_uri = %s",
                (health_uri,),
            )

    print(f"pgvector: {vector_version[0]}")
    print("LangGraph checkpoints: ready")
    print("Document vector tables: ready")
    print("Three specialist pgvector ranking runs: ready")
    print("Final report persistence round trip: ready")


if __name__ == "__main__":
    main()
