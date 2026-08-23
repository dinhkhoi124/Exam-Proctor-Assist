"""Keep RAG document management rows aligned with the on-disk index."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import RAG_DATA_DIR, VECTOR_STORE_DIR
from app.models import (  # noqa: F401 - register the complete ORM relationship graph
    chat_log,
    chat_session,
    chat_topic,
    feedback_log,
    user,
    user_activity,
)
from app.models.rag_document import RagDocument


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_index_metadata(vector_store_dir: str = VECTOR_STORE_DIR) -> list[dict]:
    metadata_path = os.path.join(vector_store_dir, "metadata.json")
    try:
        with open(metadata_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def sync_rag_documents(
    db: Session,
    metadata: list[dict],
    *,
    data_dir: str = RAG_DATA_DIR,
    refresh_existing: bool = True,
    indexed_at: datetime | None = None,
) -> dict[str, int]:
    """Insert missing PDF rows and optionally refresh every existing row.

    Rows for absent PDFs are deliberately left untouched; the delete endpoint
    owns the transition to ``deleted`` after its index rebuild succeeds.
    """
    chunk_counts: dict[str, int] = {}
    for item in metadata:
        source = item.get("source")
        if source:
            chunk_counts[str(source)] = chunk_counts.get(str(source), 0) + 1

    os.makedirs(data_dir, exist_ok=True)
    existing = {document.file_name: document for document in db.query(RagDocument).all()}
    synchronized_at = indexed_at or datetime.now(timezone.utc)
    synchronized: dict[str, int] = {}

    entries = sorted(
        (
            entry
            for entry in os.scandir(data_dir)
            if entry.is_file() and Path(entry.name).suffix.lower() == ".pdf"
        ),
        key=lambda entry: entry.name.casefold(),
    )
    for entry in entries:
        document = existing.get(entry.name)
        is_new = document is None
        if is_new:
            document = RagDocument(file_name=entry.name, storage_path=entry.path)
            db.add(document)

        chunk_count = chunk_counts.get(entry.name, 0)
        synchronized[entry.name] = chunk_count
        if is_new or refresh_existing:
            document.storage_path = entry.path
            document.file_size = entry.stat().st_size
            document.checksum_sha256 = _sha256(entry.path)
            document.status = "ready"
            document.chunk_count = chunk_count
            document.indexed_at = synchronized_at
            document.error_message = None
            document.deleted_at = None

    db.commit()
    return synchronized


def sync_rag_documents_from_index(
    db: Session,
    *,
    data_dir: str = RAG_DATA_DIR,
    vector_store_dir: str = VECTOR_STORE_DIR,
    refresh_existing: bool = True,
) -> dict[str, int]:
    return sync_rag_documents(
        db,
        load_index_metadata(vector_store_dir),
        data_dir=data_dir,
        refresh_existing=refresh_existing,
    )
