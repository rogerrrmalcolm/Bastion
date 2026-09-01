import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import document_retrieval
from document_retrieval import DocumentChunk
from agents.orchestrator_agent import DEFAULT_PLAN


class DocumentRetrievalTests(unittest.TestCase):
    def test_extract_s3_uris_deduplicates_and_strips_punctuation(self):
        text = (
            "Buyer: s3://bastion/buyer.pdf. "
            "Target: s3://bastion/target.pdf) "
            "Again: s3://bastion/buyer.pdf"
        )
        self.assertEqual(
            document_retrieval.extract_s3_uris(text),
            ["s3://bastion/buyer.pdf", "s3://bastion/target.pdf"],
        )

    def test_agent_contexts_rank_embedding_matches_and_keep_sources(self):
        chunks = [
            DocumentChunk(
                source_uri="s3://bastion/target.pdf",
                filename="target.pdf",
                page=4,
                chunk_index=0,
                text="Revenue and EBITDA increased while working capital declined.",
            ),
            DocumentChunk(
                source_uri="s3://bastion/target.pdf",
                filename="target.pdf",
                page=9,
                chunk_index=0,
                text="A regulatory investigation creates a potential closing risk.",
            ),
        ]
        calls = 0

        def fake_embedder(texts, *, task_type):
            nonlocal calls
            calls += 1
            if task_type == "RETRIEVAL_DOCUMENT":
                return [[1.0, 0.0], [0.0, 1.0]]
            vectors = []
            for text in texts:
                vectors.append(
                    [1.0, 0.0]
                    if "revenue growth margins" in text.lower()
                    else [0.0, 1.0]
                )
            return vectors

        with (
            patch.object(document_retrieval, "_download_pdf", return_value=b"pdf"),
            patch.object(document_retrieval, "extract_pdf_chunks", return_value=chunks),
        ):
            contexts, stats = document_retrieval.build_agent_document_contexts(
                "Analyze s3://bastion/target.pdf",
                DEFAULT_PLAN,
                embedder=fake_embedder,
            )

        self.assertGreaterEqual(calls, 2)
        self.assertEqual(
            stats,
            {
                "documents": 1,
                "pages": 2,
                "chunks": 2,
                "query_embedding_cache_hits": 0,
                "query_embedding_cache_misses": 3,
                "pgvector_queries": 0,
            },
        )
        self.assertIn("target.pdf, page 4", contexts["financial_agent"])
        self.assertIn("target.pdf, page 9", contexts["risk_agent"])
        self.assertLess(
            contexts["financial_agent"].find("page 4"),
            contexts["financial_agent"].find("page 9"),
        )
        self.assertLess(
            contexts["risk_agent"].find("page 9"),
            contexts["risk_agent"].find("page 4"),
        )

    def test_no_uploaded_documents_skips_embeddings(self):
        def fail_embedder(*_, **__):
            raise AssertionError("Embeddings should not run without S3 documents")

        contexts, stats = document_retrieval.build_agent_document_contexts(
            "Buyer and target context without uploads.",
            DEFAULT_PLAN,
            embedder=fail_embedder,
        )
        self.assertEqual(contexts, {})
        self.assertEqual(stats, {"documents": 0, "pages": 0, "chunks": 0})

    def test_supabase_store_persists_new_chunks_and_serves_matches(self):
        chunks = [
            DocumentChunk(
                source_uri="s3://bastion/target.pdf",
                filename="target.pdf",
                page=2,
                chunk_index=0,
                text="Revenue increased and margins expanded.",
            )
        ]

        class FakeStore:
            def __init__(self):
                self.replacements = []
                self.match_calls = []

            def get_document_statuses(self, _uris):
                return {}

            def replace_document_chunks(self, **kwargs):
                self.replacements.append(kwargs)

            def match_chunks(self, **kwargs):
                self.match_calls.append(kwargs)
                return [
                    {
                        "source_uri": "s3://bastion/target.pdf",
                        "filename": "target.pdf",
                        "page": 2,
                        "chunk_index": 0,
                        "content": "Revenue increased and margins expanded.",
                        "similarity": 0.93,
                    }
                ]

        def fake_embedder(texts, *, task_type):
            if task_type == "RETRIEVAL_DOCUMENT":
                return [[1.0, 0.0] for _ in texts]
            return [[1.0, 0.0] for _ in texts]

        store = FakeStore()
        with (
            patch.object(document_retrieval, "_download_pdf", return_value=b"pdf"),
            patch.object(document_retrieval, "extract_pdf_chunks", return_value=chunks),
        ):
            contexts, stats = document_retrieval.build_agent_document_contexts(
                "Analyze s3://bastion/target.pdf",
                DEFAULT_PLAN,
                embedder=fake_embedder,
                document_store=store,
            )

        self.assertEqual(len(store.replacements), 1)
        self.assertEqual(store.replacements[0]["embedding_dimensions"], 768)
        self.assertEqual(store.replacements[0]["chunks"][0]["embedding"], [1.0, 0.0])
        self.assertEqual(
            stats,
            {
                "documents": 1,
                "pages": 1,
                "chunks": 1,
                "query_embedding_cache_hits": 0,
                "query_embedding_cache_misses": 3,
                "pgvector_queries": 3,
            },
        )
        self.assertEqual(len(store.match_calls), 3)
        self.assertIn("target.pdf, page 2", contexts["financial_agent"])
        self.assertIn("similarity 0.930", contexts["financial_agent"])

    def test_query_cache_skips_reembedding_but_never_skips_pgvector_search(self):
        class FakeCache:
            def __init__(self):
                self.values = {}

            def get(self, query):
                return self.values.get(query)

            def set(self, query, vector):
                self.values[query] = vector

        class ReadyStore:
            def __init__(self):
                self.match_calls = 0

            def get_document_statuses(self, uris):
                return {
                    uris[0]: {
                        "page_count": 1,
                        "chunk_count": 1,
                        "embedding_model": document_retrieval.DEFAULT_EMBEDDING_MODEL,
                        "embedding_dimensions": document_retrieval.EMBEDDING_DIMENSIONS,
                    }
                }

            def replace_document_chunks(self, **_kwargs):
                raise AssertionError("Ready documents should not be re-embedded")

            def match_chunks(self, **_kwargs):
                self.match_calls += 1
                return [
                    {
                        "source_uri": "s3://bastion/target.pdf",
                        "filename": "target.pdf",
                        "page": 1,
                        "chunk_index": 0,
                        "content": "Relevant source text.",
                        "similarity": 0.88,
                    }
                ]

        embedding_calls = 0

        def fake_embedder(texts, *, task_type):
            nonlocal embedding_calls
            self.assertEqual(task_type, "RETRIEVAL_QUERY")
            embedding_calls += 1
            return [[1.0, 0.0] for _ in texts]

        store = ReadyStore()
        cache = FakeCache()
        first = document_retrieval.build_agent_document_contexts(
            "Analyze s3://bastion/target.pdf",
            DEFAULT_PLAN,
            embedder=fake_embedder,
            document_store=store,
            query_embedding_cache=cache,
        )[1]
        second = document_retrieval.build_agent_document_contexts(
            "Analyze s3://bastion/target.pdf",
            DEFAULT_PLAN,
            embedder=fake_embedder,
            document_store=store,
            query_embedding_cache=cache,
        )[1]

        self.assertEqual(embedding_calls, 1)
        self.assertEqual(first["query_embedding_cache_misses"], 3)
        self.assertEqual(second["query_embedding_cache_hits"], 3)
        self.assertEqual(store.match_calls, 6)
        self.assertEqual(first["pgvector_queries"], 3)
        self.assertEqual(second["pgvector_queries"], 3)


if __name__ == "__main__":
    unittest.main()
