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


def _combine_hybrid_results(dense_results: list, sparse_results: list, alpha: float = 0.6) -> list:
    combined_scores = {}
    
    for i, res in enumerate(dense_results):
        idx = i
        score = _normalize_score(1.0 / (i + 1), 1.0)
        combined_scores[idx] = alpha * score
    
    if sparse_results:
        max_bm25_score = max([score for _, score in sparse_results]) if sparse_results else 1.0
        for idx, bm25_score in sparse_results:
            norm_score = _normalize_score(bm25_score, max_bm25_score)
            if idx in combined_scores:
                combined_scores[idx] += (1 - alpha) * norm_score
            else:
                combined_scores[idx] = (1 - alpha) * norm_score
    
    sorted_indices = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    
    combined = []
    for idx, score in sorted_indices:
        if idx < len(dense_results):
            res = dense_results[idx].copy()
            res['combined_score'] = score
            combined.append(res)
    
    return combined


def retrieve_context(query: str, top_k: int = 15, use_rerank: bool = False):
    # Keep a stable resource pair while another thread may reload a new index.
    vector_store, bm25_retriever = _resources

    if not vector_store.metadata and not bm25_retriever.corpus:
        return "No documents found. Please build index first.", []
    
    # Dense search
    dense_results = vector_store.search(query, top_k=top_k)
    
    # BM25 search
    sparse_results = bm25_retriever.search(query, top_k=top_k)
    
    # Combine
    combined_results = _combine_hybrid_results(dense_results, sparse_results, alpha=0.65)
    
    if not combined_results:
        return "No relevant documents found.", []
    
    candidates = combined_results[:top_k]
    
    # Rerank if needed
    if use_rerank and len(candidates) > 5:
        candidates = _reranker.rerank(query, candidates, top_k=top_k)
    
    # Source analysis
    source_counts = Counter([res.get('source') for res in candidates if res.get('source')])
    if not source_counts:
        return "No documents found.", []
    
    best_source = source_counts.most_common(1)[0][0]
    
    # Filter by source
    filtered_results = []
    for res in candidates:
        if res.get('source') == best_source:
            filtered_results.append(res)
    
    if len(filtered_results) < 3:
        for res in candidates:
            if res.get('source') != best_source:
                filtered_results.append(res)
            if len(filtered_results) >= 6:
                break
    
    # Sort by page
    filtered_results.sort(key=lambda x: (x.get('source'), x.get('page', 0)))
    
    # Dedup by page
    seen_page_ids = set()
    final_to_process = []
    for res in filtered_results:
        page_id = f"{res.get('source')}_{res.get('page')}"
        if page_id not in seen_page_ids:
            final_to_process.append({
                "source": res.get('source'),
                "page": res.get('page'),
                "content": res.get('text', '')
            })
            seen_page_ids.add(page_id)
    
    # Dedup images
    unique_pages = get_unique_pages(final_to_process)
    
    # Final output
    final_pages = unique_pages[:5]
    context_parts = []
    source_documents = []
    
    for item in final_pages:
        context_parts.append(f"--- Source: {item['source']} (Page {item['page']}) ---\n{item['content']}")
        source_documents.append({
            "file_name": item['source'],
            "page": item['page'],
            "image_base64": item.get('image_base64')
        })
    
    return "\n\n".join(context_parts), source_documents
    source_documents = []

    for item in final_pages:
        context_parts.append(f"--- Nguồn: {item['source']} (Trang {item['page']}) ---\n{item['content']}")
        source_documents.append({
            "file_name": item['source'],
            "page": item['page'],
            "image_base64": item.get('image_base64')
        })

    return "\n\n".join(context_parts), source_documents
