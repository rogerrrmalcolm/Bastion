from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required for durable LangGraph checkpointing."
        )
    return database_url


@lru_cache(maxsize=1)
def get_postgres_checkpointer():
    """Create one pooled PostgreSQL checkpointer for the API process."""

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(
        conninfo=_database_url(),
        min_size=int(os.getenv("POSTGRES_POOL_MIN_SIZE", "1")),
        max_size=int(os.getenv("POSTGRES_POOL_MAX_SIZE", "10")),
        kwargs={"autocommit": True, "row_factory": dict_row},
    )
    return PostgresSaver(pool)


def setup_checkpoint_tables() -> None:
    """Run the idempotent LangGraph checkpoint migration during deployment."""
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(_database_url()) as checkpointer:
        checkpointer.setup()


if __name__ == "__main__":
    setup_checkpoint_tables()
