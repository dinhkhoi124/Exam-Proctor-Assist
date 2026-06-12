import os
import shutil
import tempfile

from app.core.config import RAG_DATA_DIR, VECTOR_STORE_DIR
from app.rag.chunker import semantic_chunk
from app.rag.embedder import BM25Retriever, VectorStore
from app.rag.parser import load_pdf


INDEX_FILES = ("index.faiss", "metadata.json", "bm25.pkl", "bm25_corpus.json")


def build_index(
    data_dir: str = RAG_DATA_DIR,
    output_dir: str = VECTOR_STORE_DIR,
    return_resources: bool = False,
    progress_callback=None,
):
    """Build a complete RAG index and replace the active index atomically per file."""
    def report(progress: int, stage: str):
        if progress_callback:
            progress_callback(progress, stage)

    report(20, "reading_documents")
    docs = load_pdf(data_dir)
    report(35, "chunking_documents")
    chunks = semantic_chunk(docs)

    texts = []
    metadata = []
    for chunk in chunks:
        clean_text = chunk["text"].strip()
        if len(clean_text) < 20:
            continue

        texts.append(clean_text)
        metadata.append(
            {
                "text": clean_text,
                "page": chunk["page"],
                "source": chunk.get("source", "unknown.pdf"),
            }
        )

    os.makedirs(output_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="rag-index-", dir=os.path.dirname(output_dir))
    backup_dir = tempfile.mkdtemp(prefix="rag-index-backup-", dir=os.path.dirname(output_dir))
    installed_files = []
    try:
        store = VectorStore()
        if texts:
            report(50, "creating_embeddings")
            store.add(texts, metadata)
        report(82, "saving_vector_index")
        store.save(temp_dir)

        bm25_retriever = BM25Retriever()
        if texts:
            bm25_retriever.build(texts)
        report(90, "saving_search_index")
        bm25_retriever.save(temp_dir)

        report(95, "activating_index")
        for file_name in INDEX_FILES:
            active_path = os.path.join(output_dir, file_name)
            backup_path = os.path.join(backup_dir, file_name)
            if os.path.exists(active_path):
                os.replace(active_path, backup_path)
            os.replace(
                os.path.join(temp_dir, file_name),
                active_path,
            )
            installed_files.append(file_name)
    except Exception:
        for file_name in installed_files:
            active_path = os.path.join(output_dir, file_name)
            if os.path.exists(active_path):
                os.remove(active_path)
        for file_name in INDEX_FILES:
            backup_path = os.path.join(backup_dir, file_name)
            if os.path.exists(backup_path):
                os.replace(backup_path, os.path.join(output_dir, file_name))
        raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(backup_dir, ignore_errors=True)

    if return_resources:
        report(100, "completed")
        return len(texts), store, bm25_retriever
    report(100, "completed")
    return len(texts)


if __name__ == "__main__":
    chunk_count = build_index()
    print(f"RAG index built successfully with {chunk_count} chunks.")
