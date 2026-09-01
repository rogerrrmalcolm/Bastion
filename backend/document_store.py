from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import configuration  # noqa: F401

UPSERT_BATCH_SIZE = 100


class SupabaseDocumentStore:
    """Persist and retrieve PDF chunks through Supabase Postgres + pgvector."""

    def __init__(self, client=None) -> None:
        if client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                raise RuntimeError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required "
                    "for persistent document retrieval."
                )
            from supabase import create_client

            client = create_client(url, key)
        self._client = client

    def get_document_statuses(self, source_uris: list[str]) -> dict[str, dict[str, Any]]:
        if not source_uris:
            return {}
        response = (
            self._client.table("documents")
            .select(
                "id,source_uri,filename,page_count,chunk_count,"
                "embedding_model,embedding_dimensions"
            )
            .in_("source_uri", source_uris)
            .execute()
        )
        return {row["source_uri"]: row for row in (response.data or [])}

    def replace_document_chunks(
        self,
        *,
        source_uri: str,
        filename: str,
        page_count: int,
        chunks: list[dict[str, Any]],
        embedding_model: str,
        embedding_dimensions: int,
    ) -> None:
        document_response = (
            self._client.table("documents")
            .upsert(
                {
                    "source_uri": source_uri,
                    "filename": filename,
                    "page_count": page_count,
                    "chunk_count": len(chunks),
                    "embedding_model": embedding_model,
                    "embedding_dimensions": embedding_dimensions,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="source_uri",
            )
            .execute()
        )
        rows = document_response.data or []
        if not rows:
            raise RuntimeError(f"Supabase did not return a document id for {source_uri}.")
        document_id = rows[0]["id"]
        self._client.table("document_chunks").delete().eq(
            "document_id", document_id
        ).execute()

        records = [
            {
                "document_id": document_id,
                "page": chunk["page"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": chunk["embedding"],
            }
            for chunk in chunks
        ]
        for start in range(0, len(records), UPSERT_BATCH_SIZE):
            self._client.table("document_chunks").insert(
                records[start : start + UPSERT_BATCH_SIZE]
            ).execute()

    def match_chunks(
        self,
        *,
        query_embedding: list[float],
        source_uris: list[str],
        match_count: int,
    ) -> list[dict[str, Any]]:
        response = self._client.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "source_uris": source_uris,
                "match_count": match_count,
            },
        ).execute()
        return list(response.data or [])


def supabase_document_store_is_configured() -> bool:
    return bool(
        os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )


@lru_cache(maxsize=1)
def get_supabase_document_store() -> SupabaseDocumentStore:
    return SupabaseDocumentStore()
