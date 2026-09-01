import io
import math
import os
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

import boto3
from pypdf import PdfReader

from document_store import (
    get_supabase_document_store,
    supabase_document_store_is_configured,
)
from embedding_cache import get_query_embedding_cache
from gemini_client import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    call_gemini_embeddings,
)
from schemas import OrchestrationPlan

S3_URI_PATTERN = re.compile(r"s3://[A-Za-z0-9._-]+/[^\s]+")
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 240
EMBEDDING_BATCH_SIZE = 64
MAX_DOCUMENTS = 10
MAX_PAGES = 500
TOP_K_PER_AGENT = 6
MAX_CONTEXT_CHARS = 7000
_DEFAULT_DOCUMENT_STORE = object()
_DEFAULT_QUERY_CACHE = object()

AGENT_RETRIEVAL_LENSES = {
    "market_agent": (
        "market size demand customers competition pricing sector trends growth "
        "geography products and commercial positioning"
    ),
    "financial_agent": (
        "revenue growth margins EBITDA cash flow working capital debt liquidity "
        "customer concentration forecasts and quality of earnings"
    ),
    "risk_agent": (
        "legal regulatory cyber privacy tax operational integration contracts "
        "litigation compliance liabilities and acquisition risks"
    ),
}


@dataclass(frozen=True)
class DocumentChunk:
    source_uri: str
    filename: str
    page: int
    chunk_index: int
    text: str
    embedding: tuple[float, ...] = ()
    similarity: float | None = None


def extract_s3_uris(text: str) -> list[str]:
    uris: list[str] = []
    seen: set[str] = set()
    for match in S3_URI_PATTERN.findall(text):
        uri = match.rstrip(".,;:)]}")
        if uri not in seen:
            uris.append(uri)
            seen.add(uri)
    return uris[:MAX_DOCUMENTS]


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def _s3_client():
    region = os.getenv("AWS_REGION")
    return boto3.client("s3", region_name=region) if region else boto3.client("s3")


def _download_pdf(uri: str, client=None) -> bytes:
    bucket, key = _parse_s3_uri(uri)
    configured_bucket = os.getenv("S3_BUCKET")
    if configured_bucket and bucket != configured_bucket:
        raise ValueError(f"S3 URI bucket is not the configured Bastion bucket: {bucket}")
    response = (client or _s3_client()).get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_page(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= CHUNK_SIZE:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + CHUNK_SIZE)
        if end < len(cleaned):
            boundary = cleaned.rfind(" ", start + CHUNK_SIZE // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks


def extract_pdf_chunks(uri: str, pdf_bytes: bytes) -> list[DocumentChunk]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    filename = _parse_s3_uri(uri)[1].rsplit("/", 1)[-1]
    chunks: list[DocumentChunk] = []
    for page_number, page in enumerate(reader.pages[:MAX_PAGES], start=1):
        for chunk_index, text in enumerate(_split_page(page.extract_text() or "")):
            chunks.append(
                DocumentChunk(
                    source_uri=uri,
                    filename=filename,
                    page=page_number,
                    chunk_index=chunk_index,
                    text=text,
                )
            )
    return chunks


def _embed_batches(
    texts: list[str],
    task_type: str,
    embedder: Callable[..., list[list[float]]],
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        vectors.extend(
            embedder(
                texts[start:start + EMBEDDING_BATCH_SIZE],
                task_type=task_type,
            )
        )
    return vectors


def _embed_specialist_queries(
    queries: list[str],
    embedder: Callable[..., list[list[float]]],
    cache,
) -> tuple[list[list[float]], int, int]:
    """Resolve query vectors while leaving every downstream retrieval uncached."""
    vectors: list[list[float] | None] = [None] * len(queries)
    missing_indexes: list[int] = []
    cache_hits = 0

    for index, query in enumerate(queries):
        cached = cache.get(query) if cache is not None else None
        if cached is None:
            missing_indexes.append(index)
        else:
            vectors[index] = cached
            cache_hits += 1

    missing_queries = [queries[index] for index in missing_indexes]
    generated = _embed_batches(missing_queries, "RETRIEVAL_QUERY", embedder)
    if len(generated) != len(missing_indexes):
        raise RuntimeError("Embedding count did not match specialist queries.")

    for index, vector in zip(missing_indexes, generated, strict=True):
        vectors[index] = vector
        if cache is not None:
            cache.set(queries[index], vector)

    return (
        [vector for vector in vectors if vector is not None],
        cache_hits,
        len(missing_indexes),
    )


def _cosine_similarity(left: tuple[float, ...], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return -1.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return numerator / (left_norm * right_norm)


def _agent_queries(plan: OrchestrationPlan) -> dict[str, str]:
    queries: dict[str, str] = {}
    for step in plan.steps:
        if step.agent_name not in AGENT_RETRIEVAL_LENSES:
            continue
        queries[step.agent_name] = "\n".join(
            [
                AGENT_RETRIEVAL_LENSES[step.agent_name],
                step.objective,
                *step.context_needed,
                *[tool.purpose for tool in step.tools],
            ]
        )
    return queries


def _format_context(chunks: list[DocumentChunk]) -> str:
    sections: list[str] = []
    used_chars = 0
    for chunk in chunks:
        relevance = (
            f", similarity {chunk.similarity:.3f}"
            if chunk.similarity is not None
            else ""
        )
        section = (
            f"Source: {chunk.filename}, page {chunk.page} "
            f"({chunk.source_uri}{relevance})\nExcerpt: {chunk.text}"
        )
        if sections and used_chars + len(section) > MAX_CONTEXT_CHARS:
            break
        sections.append(section)
        used_chars += len(section)
    return "\n\n".join(sections)


def build_agent_document_contexts(
    company_text: str,
    plan: OrchestrationPlan,
    *,
    s3_client=None,
    embedder: Callable[..., list[list[float]]] = call_gemini_embeddings,
    document_store=_DEFAULT_DOCUMENT_STORE,
    query_embedding_cache=_DEFAULT_QUERY_CACHE,
) -> tuple[dict[str, str], dict[str, int]]:
    uris = extract_s3_uris(company_text)
    if not uris:
        return {}, {"documents": 0, "pages": 0, "chunks": 0}

    if document_store is _DEFAULT_DOCUMENT_STORE:
        document_store = (
            get_supabase_document_store()
            if embedder is call_gemini_embeddings
            and supabase_document_store_is_configured()
            else None
        )
    if query_embedding_cache is _DEFAULT_QUERY_CACHE:
        query_embedding_cache = (
            get_query_embedding_cache()
            if embedder is call_gemini_embeddings
            else None
        )

    if document_store is not None:
        statuses = document_store.get_document_statuses(uris)
        stale_uris = [
            uri
            for uri in uris
            if uri not in statuses
            or statuses[uri]["embedding_model"] != DEFAULT_EMBEDDING_MODEL
            or statuses[uri]["embedding_dimensions"] != EMBEDDING_DIMENSIONS
        ]
        new_chunks: list[DocumentChunk] = []
        chunks_by_uri: dict[str, list[DocumentChunk]] = {}
        for uri in stale_uris:
            extracted = extract_pdf_chunks(uri, _download_pdf(uri, s3_client))
            chunks_by_uri[uri] = extracted
            new_chunks.extend(extracted)

        if new_chunks:
            vectors = _embed_batches(
                [chunk.text for chunk in new_chunks],
                "RETRIEVAL_DOCUMENT",
                embedder,
            )
            if len(vectors) != len(new_chunks):
                raise RuntimeError(
                    "Embedding count did not match extracted document chunks."
                )
            vector_by_chunk = {
                (chunk.source_uri, chunk.page, chunk.chunk_index): vector
                for chunk, vector in zip(new_chunks, vectors)
            }
        else:
            vector_by_chunk = {}

        for uri in stale_uris:
            extracted = chunks_by_uri[uri]
            page_count = len({chunk.page for chunk in extracted})
            document_store.replace_document_chunks(
                source_uri=uri,
                filename=(
                    extracted[0].filename
                    if extracted
                    else _parse_s3_uri(uri)[1].rsplit("/", 1)[-1]
                ),
                page_count=page_count,
                chunks=[
                    {
                        "page": chunk.page,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.text,
                        "embedding": vector_by_chunk[
                            (chunk.source_uri, chunk.page, chunk.chunk_index)
                        ],
                    }
                    for chunk in extracted
                ],
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                embedding_dimensions=EMBEDDING_DIMENSIONS,
            )
            statuses[uri] = {
                "page_count": page_count,
                "chunk_count": len(extracted),
                "embedding_model": DEFAULT_EMBEDDING_MODEL,
                "embedding_dimensions": EMBEDDING_DIMENSIONS,
            }

        queries = _agent_queries(plan)
        query_names = list(queries)
        query_vectors, cache_hits, cache_misses = _embed_specialist_queries(
            [queries[name] for name in query_names],
            embedder,
            query_embedding_cache,
        )

        contexts = {}
        for agent_name, query_vector in zip(query_names, query_vectors):
            matches = document_store.match_chunks(
                query_embedding=query_vector,
                source_uris=uris,
                match_count=TOP_K_PER_AGENT,
            )
            contexts[agent_name] = _format_context(
                [
                    DocumentChunk(
                        source_uri=row["source_uri"],
                        filename=row["filename"],
                        page=row["page"],
                        chunk_index=row["chunk_index"],
                        text=row["content"],
                        similarity=float(row["similarity"]),
                    )
                    for row in matches
                ]
            )

        return contexts, {
            "documents": len(uris),
            "pages": sum(status["page_count"] for status in statuses.values()),
            "chunks": sum(status["chunk_count"] for status in statuses.values()),
            "query_embedding_cache_hits": cache_hits,
            "query_embedding_cache_misses": cache_misses,
            "pgvector_queries": len(query_names),
        }

    chunks: list[DocumentChunk] = []
    for uri in uris:
        chunks.extend(extract_pdf_chunks(uri, _download_pdf(uri, s3_client)))
    if not chunks:
        return {}, {"documents": len(uris), "pages": 0, "chunks": 0}

    vectors = _embed_batches(
        [chunk.text for chunk in chunks],
        "RETRIEVAL_DOCUMENT",
        embedder,
    )
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding count did not match extracted document chunks.")
    indexed_chunks = [
        DocumentChunk(**{**chunk.__dict__, "embedding": tuple(vector)})
        for chunk, vector in zip(chunks, vectors)
    ]

    queries = _agent_queries(plan)
    query_names = list(queries)
    query_vectors, cache_hits, cache_misses = _embed_specialist_queries(
        [queries[name] for name in query_names],
        embedder,
        query_embedding_cache,
    )
    contexts: dict[str, str] = {}
    for agent_name, query_vector in zip(query_names, query_vectors):
        ranked = sorted(
            indexed_chunks,
            key=lambda chunk: _cosine_similarity(chunk.embedding, query_vector),
            reverse=True,
        )[:TOP_K_PER_AGENT]
        contexts[agent_name] = _format_context(ranked)

    page_count = len({(chunk.source_uri, chunk.page) for chunk in chunks})
    return contexts, {
        "documents": len(uris),
        "pages": page_count,
        "chunks": len(chunks),
        "query_embedding_cache_hits": cache_hits,
        "query_embedding_cache_misses": cache_misses,
        "pgvector_queries": 0,
    }
