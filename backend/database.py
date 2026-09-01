from __future__ import annotations

import os
from functools import lru_cache

import configuration  # noqa: F401


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError(
            "DATABASE_URL is required for PostgreSQL checkpoints and reports."
        )
    return value


@lru_cache(maxsize=1)
def get_postgres_pool():
    """Return the process-local pool connected to the shared PostgreSQL database."""
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    return ConnectionPool(
        conninfo=database_url(),
        min_size=int(os.getenv("POSTGRES_POOL_MIN_SIZE", "1")),
        max_size=int(os.getenv("POSTGRES_POOL_MAX_SIZE", "10")),
        kwargs={"autocommit": True, "row_factory": dict_row},
    )
