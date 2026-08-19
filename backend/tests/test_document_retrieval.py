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
        self.assertEqual(stats, {"documents": 1, "pages": 2, "chunks": 2})
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


if __name__ == "__main__":
    unittest.main()
