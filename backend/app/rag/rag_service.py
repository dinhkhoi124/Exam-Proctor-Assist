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


def _combine_hybrid_results(
    dense_results: list, sparse_results: list, alpha: float = 0.6
) -> list:
    combined_scores = {}

    for i, _res in enumerate(dense_results):
        score = _normalize_score(1.0 / (i + 1), 1.0)
        combined_scores[i] = alpha * score

    if sparse_results:
        max_bm25_score = max(score for _, score in sparse_results)
        for idx, bm25_score in sparse_results:
            norm_score = _normalize_score(bm25_score, max_bm25_score)
            if idx in combined_scores:
                combined_scores[idx] += (1 - alpha) * norm_score
            else:
                combined_scores[idx] = (1 - alpha) * norm_score

    sorted_indices = sorted(
        combined_scores.items(), key=lambda item: item[1], reverse=True
    )

    combined = []
    for idx, score in sorted_indices:
        if idx < len(dense_results):
            result = dense_results[idx].copy()
            result["combined_score"] = score
            combined.append(result)
    return combined


def _select_final_pages(candidates: list) -> list:
    source_counts = Counter(
        result.get("source") for result in candidates if result.get("source")
    )
    if not source_counts:
        return []

    best_source = source_counts.most_common(1)[0][0]
    filtered_results = [
        result for result in candidates if result.get("source") == best_source
    ]

    if len(filtered_results) < 3:
        for result in candidates:
            if result.get("source") != best_source:
                filtered_results.append(result)
            if len(filtered_results) >= 6:
                break

    filtered_results.sort(
        key=lambda result: (result.get("source"), result.get("page", 0))
    )

    seen_page_ids = set()
    final_to_process = []
    for result in filtered_results:
        page_id = f"{result.get('source')}_{result.get('page')}"
        if page_id in seen_page_ids:
            continue
        final_to_process.append(
            {
                "source": result.get("source"),
                "page": result.get("page"),
                "content": result.get("text", ""),
            }
        )
        seen_page_ids.add(page_id)

    return get_unique_pages(final_to_process)[:5]


def retrieve_ranked(query: str, top_k: int = 15, use_rerank: bool = False) -> dict:
    """Return ranked candidates and final pages used by the production prompt."""
    vector_store, bm25_retriever = _resources
    if not vector_store.metadata and not bm25_retriever.corpus:
        return {"status": "empty_index", "candidates": [], "final_pages": []}

    dense_results = vector_store.search(query, top_k=top_k)
    sparse_results = bm25_retriever.search(query, top_k=top_k)
    combined_results = _combine_hybrid_results(
        dense_results, sparse_results, alpha=0.65
    )
    if not combined_results:
        return {"status": "no_results", "candidates": [], "final_pages": []}

    candidates = combined_results[:top_k]
    if use_rerank and len(candidates) > 5:
        candidates = _reranker.rerank(query, candidates, top_k=top_k)

    ranked_candidates = []
    for rank, candidate in enumerate(candidates, start=1):
        ranked = candidate.copy()
        ranked["rank"] = rank
        ranked_candidates.append(ranked)

    final_pages = _select_final_pages(candidates)
    status = "ok" if final_pages else "no_sources"
    return {
        "status": status,
        "candidates": ranked_candidates,
        "final_pages": final_pages,
    }


def retrieve_context(query: str, top_k: int = 15, use_rerank: bool = False):
    retrieval = retrieve_ranked(query, top_k=top_k, use_rerank=use_rerank)
    final_pages = retrieval["final_pages"]
    if not final_pages:
        status_messages = {
            "empty_index": "No documents found. Please build index first.",
            "no_results": "No relevant documents found.",
            "no_sources": "No documents found.",
        }
        return status_messages.get(retrieval["status"], ""), []

    context_parts = []
    source_documents = []
    for item in final_pages:
        context_parts.append(
            f"--- Source: {item['source']} (Page {item['page']}) ---\n{item['content']}"
        )
        source_documents.append(
            {
                "file_name": item["source"],
                "page": item["page"],
                "image_base64": item.get("image_base64"),
            }
        )

    return "\n\n".join(context_parts), source_documents
