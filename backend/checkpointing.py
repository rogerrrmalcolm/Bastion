from __future__ import annotations

from functools import lru_cache

import configuration  # noqa: F401
from database import database_url, get_postgres_pool


@lru_cache(maxsize=1)
def get_postgres_checkpointer():
    """Create one pooled PostgreSQL checkpointer for the API process."""

    from langgraph.checkpoint.postgres import PostgresSaver
    return PostgresSaver(get_postgres_pool())


def setup_checkpoint_tables() -> None:
    """Run the idempotent LangGraph checkpoint migration during deployment."""
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(database_url()) as checkpointer:
        checkpointer.setup()


if __name__ == "__main__":
    setup_checkpoint_tables()
