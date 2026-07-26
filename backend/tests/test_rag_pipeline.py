import os
import sys
import types
import unittest

os.environ.setdefault("LLM_BASE_URL", "http://127.0.0.1:9/v1")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from app.rag.chunker import CHILD_MAX_LENGTH, PARENT_MAX_LENGTH, semantic_chunk
from app.rag.embedder import BM25Retriever


class ChunkerTests(unittest.TestCase):
    def test_parent_child_metadata_and_limits(self):
        text = (
            "HƯỚNG DẪN XỬ LÝ LỖI EOS\n"
            + "Sinh viên không thể đăng nhập EOSClient. "
            + "Giám thị kiểm tra Wi-Fi FU-Exam và mã dự thi. " * 18
        )
        chunks = semantic_chunk(
            [{"content": text, "page": 7, "source": "Hướng dẫn EOS.pdf"}]
        )

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk["text"]) <= CHILD_MAX_LENGTH for chunk in chunks))
        self.assertTrue(
            all(len(chunk["parent_text"]) <= PARENT_MAX_LENGTH for chunk in chunks)
        )
        self.assertTrue(all(chunk["page"] == 7 for chunk in chunks))
        self.assertTrue(all(chunk["parent_id"] for chunk in chunks))
        self.assertTrue(
            all(
                chunk["retrieval_text"].startswith(
                    "Hướng dẫn EOS > HƯỚNG DẪN XỬ LÝ LỖI EOS"
                )
                for chunk in chunks
            )
        )


class BM25TokenizerTests(unittest.TestCase):
    def test_exact_identifier_and_accent_folded_query(self):
        retriever = BM25Retriever()
        retriever.build(
            [
                "Hướng dẫn xử lý mã lỗi SEB-101 trên EOSClient",
                "Quy định thí sinh đến muộn",
                "Hướng dẫn ký tên điện tử sau khi thi",
            ]
        )

        results = retriever.search("ma loi seb-101", top_k=2)

        self.assertTrue(results)
        self.assertEqual(results[0][0], 0)


class _DummyVectorStore:
    def __init__(self, dim=768):
        self.metadata = []

    def load(self, _folder):
        return None


class _DummyBM25:
    def __init__(self):
        self.corpus = []

    def load(self, _folder):
        return None


fake_embedder = types.ModuleType("app.rag.embedder")
fake_embedder.VectorStore = _DummyVectorStore
fake_embedder.BM25Retriever = _DummyBM25
sys.modules["app.rag.embedder"] = fake_embedder

from app.rag import rag_service


class FusionTests(unittest.TestCase):
    def test_rrf_rewards_agreement_between_retrievers(self):
        metadata = [
            {"text": "agreed"},
            {"text": "dense only"},
            {"text": "bm25 only"},
        ]
        dense = [
            {"index": 0, "text": "agreed", "dense_score": 0.9},
            {"index": 1, "text": "dense only", "dense_score": 0.89},
        ]
        sparse = [(2, 10.0), (0, 9.0)]

        fused = rag_service._combine_hybrid_results(dense, sparse, metadata)

        self.assertEqual(fused[0]["index"], 0)
        self.assertTrue(fused[0]["matched_both"])

    def test_confidence_gate_requires_one_strong_signal(self):
        weak_dense = [{"dense_score": 0.81}]
        weak_sparse = [(3, 19.0)]

        self.assertFalse(
            rag_service._has_sufficient_retrieval_signal(
                weak_dense,
                weak_sparse,
                min_dense_score=0.84,
                min_bm25_score=20.0,
            )
        )
        self.assertTrue(
            rag_service._has_sufficient_retrieval_signal(
                [{"dense_score": 0.85}],
                [],
                min_dense_score=0.84,
                min_bm25_score=20.0,
            )
        )
        self.assertTrue(
            rag_service._has_sufficient_retrieval_signal(
                weak_dense,
                [(3, 21.0)],
                min_dense_score=0.84,
                min_bm25_score=20.0,
            )
        )

    def test_parent_aggregation_and_text_dedup(self):
        children = [
            {
                "parent_id": "p1",
                "source": "a.pdf",
                "page": 4,
                "parent_text": "Cách xử lý lỗi đăng nhập EOS.",
                "combined_score": 0.02,
            },
            {
                "parent_id": "p1",
                "source": "a.pdf",
                "page": 4,
                "parent_text": "Cách xử lý lỗi đăng nhập EOS.",
                "combined_score": 0.019,
            },
            {
                "parent_id": "p2",
                "source": "copy.pdf",
                "page": 8,
                "parent_text": "Cách xử lý lỗi đăng nhập EOS.",
                "combined_score": 0.018,
            },
        ]

        parents = rag_service._aggregate_parents(children)
        selected = rag_service._select_context_parents(parents, top_k=5)

        self.assertEqual(len(parents), 2)
        self.assertEqual(parents[0]["parent_id"], "p1")
        self.assertEqual(len(selected), 1)


if __name__ == "__main__":
    unittest.main()

