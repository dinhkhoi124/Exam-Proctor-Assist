"""Snapshot and restore the active on-disk RAG index around document updates."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class RagIndexSnapshot:
    vector_store_dir: str
    backup_dir: str
    existing_files: dict[str, bool]


class RagRollbackError(RuntimeError):
    """Raised after every rollback step ran but at least one step failed."""

    def __init__(self, failed_steps: list[str]):
        self.failed_steps = failed_steps
        super().__init__(
            "Document rollback was incomplete for: "
            f"{', '.join(failed_steps)}; manual recovery is required"
        )


def run_rollback_steps(
    steps: Iterable[tuple[str, Callable[[], None]]],
) -> None:
    """Run every cleanup step even if an earlier rollback operation fails."""
    failed_steps: list[str] = []
    for label, action in steps:
        try:
            action()
        except Exception:
            failed_steps.append(label)
    if failed_steps:
        raise RagRollbackError(failed_steps)


def rollback_file_changes(file_changes: list[dict]) -> None:
    """Undo only file operations that were recorded as successfully completed."""
    for change in reversed(file_changes):
        target_path = change["target_path"]
        backup_path = change["backup_path"]
        if change.get("new_installed") and os.path.exists(target_path):
            os.remove(target_path)
        if change.get("previous_moved"):
            if not os.path.exists(backup_path):
                raise FileNotFoundError(
                    f"Missing document rollback file: {os.path.basename(target_path)}"
                )
            os.replace(backup_path, target_path)


def snapshot_active_index(
    vector_store_dir: str,
    backup_dir: str,
    index_files: Iterable[str],
) -> RagIndexSnapshot:
    """Copy the currently active index so a later DB-sync failure can undo it."""
    os.makedirs(backup_dir, exist_ok=True)
    existing_files: dict[str, bool] = {}
    for file_name in index_files:
        active_path = os.path.join(vector_store_dir, file_name)
        backup_path = os.path.join(backup_dir, file_name)
        exists = os.path.isfile(active_path)
        existing_files[file_name] = exists
        if exists:
            shutil.copy2(active_path, backup_path)
    return RagIndexSnapshot(
        vector_store_dir=vector_store_dir,
        backup_dir=backup_dir,
        existing_files=existing_files,
    )


def restore_active_index(
    snapshot: RagIndexSnapshot,
    reload_resources: Callable[[], None],
) -> None:
    """Restore the old index files, then replace the in-memory resources."""
    for file_name, existed_before_update in snapshot.existing_files.items():
        active_path = os.path.join(snapshot.vector_store_dir, file_name)
        backup_path = os.path.join(snapshot.backup_dir, file_name)
        if existed_before_update:
            if not os.path.isfile(backup_path):
                raise FileNotFoundError(f"Missing RAG index rollback file: {file_name}")
            # Copy instead of moving so a second cleanup attempt can still use the backup.
            shutil.copy2(backup_path, active_path)
        elif os.path.exists(active_path):
            os.remove(active_path)

    reload_resources()
