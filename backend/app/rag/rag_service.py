import os
from collections import Counter
from app.core.config import VECTOR_STORE_DIR
from app.rag.embedder import VectorStore, BM25Retriever, CrossEncoderReranker
from app.rag.retriever import get_unique_pages 

_resources = None
_reranker = CrossEncoderReranker()


def activate_resources(vector_store: VectorStore, bm25_retriever: BM25Retriever):
    global _resources
    _resources = (vector_store, bm25_retriever)


def load_resources():
    new_vector_store = VectorStore(dim=768)
    new_bm25_retriever = BM25Retriever()

    if os.path.exists(os.path.join(VECTOR_STORE_DIR, "index.faiss")):
        new_vector_store.load(VECTOR_STORE_DIR)
    try:
        new_bm25_retriever.load(VECTOR_STORE_DIR)
    except Exception:
        pass

    activate_resources(new_vector_store, new_bm25_retriever)

load_resources()


def _normalize_score(score: float, max_score: float = 1.0) -> float:
    if max_score == 0:
        return 0
    return min(score / max_score, 1.0)


def _combine_hybrid_results(dense_results, sparse_results, alpha=0.65):
    combined = {}

    # Dense
    for res in dense_results:
        idx = res["vector_idx"]

        combined[idx] = {
            "result": res,
            "score": alpha * res["dense_score"]
        }

    # BM25
    max_bm25 = max(
        [score for _, score in sparse_results],
        default=1.0
    )

    for idx, bm25_score in sparse_results:

        normalized = bm25_score / max_bm25

        if idx in combined:
            combined[idx]["score"] += (
                (1 - alpha) * normalized
            )
        else:

            item = _resources[0].metadata[idx].copy()

            item["vector_idx"] = idx

            combined[idx] = {
                "result": item,
                "score": (1 - alpha) * normalized
            }

    ranked = sorted(
        combined.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return [x["result"] for x in ranked]


def retrieve_context(query: str, top_k: int = 15, use_rerank: bool = True):
    # Keep a stable resource pair while another thread may reload a new index.
    vector_store, bm25_retriever = _resources

    if not vector_store.metadata and not bm25_retriever.corpus:
        return "No documents found. Please build index first.", []

    # =========================
    # Dense Search
    # =========================
    dense_results = vector_store.search(query, top_k=top_k)

    # =========================
    # BM25 Search
    # =========================
    sparse_results = bm25_retriever.search(query, top_k=top_k)

    # =========================
    # Hybrid Combine
    # =========================
    combined_results = _combine_hybrid_results(
        dense_results,
        sparse_results,
        alpha=0.65
    )

    if not combined_results:
        return "No relevant documents found.", []

    candidates = combined_results[:top_k]

    # =========================
    # Rerank
    # =========================
    if use_rerank and len(candidates) > 5:
        candidates = _reranker.rerank(
            query,
            candidates,
            top_k=top_k
        )

    # =========================
    # KHÔNG lọc theo best_source nữa
    # Giữ top chunk sau rerank
    # =========================
    filtered_results = candidates[:8]

    # =========================
    # Sort theo source + page
    # =========================
    filtered_results.sort(
        key=lambda x: (
            x.get("source", ""),
            x.get("page", 0)
        )
    )

    # =========================
    # Deduplicate page
    # =========================
    seen_page_ids = set()
    final_to_process = []

    for res in filtered_results:
        page_id = f"{res.get('source')}_{res.get('page')}"

        if page_id in seen_page_ids:
            continue

        final_to_process.append({
            "source": res.get("source"),
            "page": res.get("page"),
            "content": res.get("text", "")
        })

        seen_page_ids.add(page_id)

    # =========================
    # Deduplicate image
    # =========================
    unique_pages = get_unique_pages(final_to_process)

    # =========================
    # Final pages
    # =========================
    final_pages = unique_pages[:5]

    context_parts = []
    source_documents = []

    for item in final_pages:
        context_parts.append(
            f"--- Source: {item['source']} (Page {item['page']}) ---\n"
            f"{item['content']}"
        )

        source_documents.append({
            "file_name": item["source"],
            "page": item["page"],
            "image_base64": item.get("image_base64")
        })

    return "\n\n".join(context_parts), source_documents