import os
import shutil
import subprocess
import tempfile

from app.core.config import RAG_DATA_DIR, VECTOR_STORE_DIR
from app.rag.chunker import semantic_chunk
from app.rag.embedder import BM25Retriever, VectorStore
from app.rag.parser import load_pdf
from app.rag.temporal_discovery import (
    discover_temporal_metadata,
    merge_temporal_metadata,
    save_generated_manifest,
)
from app.rag.temporal_resolver import load_temporal_manifest


INDEX_FILES = ("index.faiss", "metadata.json", "bm25.pkl", "bm25_corpus.json")
INDEX_SCHEMA_VERSION = 3


def _restore_inherited_permissions(path: str) -> None:
    """Make atomically installed files inherit the destination ACL on Windows.

    ``os.replace`` preserves the ACL of a file created in the private temporary
    build directory. A Uvicorn reload process running as the deployment user can
    otherwise receive ``Permission denied`` while reading the new FAISS index.
    """
    if os.name != "nt":
        return
    for argument in ("/inheritance:e", "/reset"):
        completed = subprocess.run(
            ["icacls", path, argument],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise OSError(f"Failed to restore inherited ACL for {path}: {detail}")


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
    generated_temporal = discover_temporal_metadata(docs)
    save_generated_manifest(generated_temporal)
    report(35, "chunking_documents")
    chunks = semantic_chunk(docs)
    temporal_manifest = merge_temporal_metadata(
        generated_temporal,
        load_temporal_manifest(),
    )

    texts = []
    metadata = []
    for chunk in chunks:
        source = chunk.get("source", "unknown.pdf")
        page = int(chunk["page"])
        source_temporal = temporal_manifest.get(source, {})
        page_overrides = source_temporal.get("_page_overrides", {})
        page_temporal = dict(page_overrides.get(str(page), {}))
        verified_visual_fact = page_temporal.pop("verified_visual_fact", None)

        child_text = chunk["text"].strip()
        retrieval_text = chunk.get("retrieval_text", child_text).strip()
        parent_text = chunk.get("parent_text", chunk.get("display_text", child_text)).strip()
        if verified_visual_fact:
            fact_text = f"Thông tin xác minh từ hình ảnh trên trang: {verified_visual_fact}"
            child_text = f"{child_text}\n{fact_text}"
            retrieval_text = f"{retrieval_text}\n{fact_text}"
            parent_text = f"{parent_text}\n{fact_text}"
        if len(child_text) < 20 or not retrieval_text or not parent_text:
            continue

        texts.append(retrieval_text)
        item_metadata = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "text": child_text,
            "retrieval_text": retrieval_text,
            "display_text": parent_text,
            "parent_text": parent_text,
            "page": page,
            "source": source,
            "document_title": chunk.get("document_title", ""),
            "heading": chunk.get("heading", ""),
            "section_path": chunk.get("section_path", ""),
            "parent_id": chunk.get("parent_id"),
            "child_id": chunk.get("child_id"),
        }
        item_metadata.update(
            {
                key: value
                for key, value in source_temporal.items()
                if key != "_page_overrides"
            }
        )
        item_metadata.update(page_temporal)
        if verified_visual_fact:
            item_metadata["verified_visual_fact"] = verified_visual_fact
        metadata.append(item_metadata)

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
            _restore_inherited_permissions(active_path)
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
    from app.db.session import SessionLocal
    from app.services.rag_document_sync import sync_rag_documents

    chunk_count, vector_store, _bm25_retriever = build_index(return_resources=True)
    database = SessionLocal()
    try:
        synchronized = sync_rag_documents(database, vector_store.metadata)
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()
    print(
        f"RAG index built successfully with {chunk_count} child chunks; "
        f"database synchronized for {len(synchronized)} PDF documents."
    )
