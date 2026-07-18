from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env")
except ImportError:
    pass


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_config(path: str | Path) -> dict:
    with resolve_path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
            if key not in {"image_base64", "base64"}
        }
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def read_jsonl(path: str | Path) -> list[dict]:
    target = Path(path)
    if not target.exists():
        return []
    with target.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def atomic_write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(json_safe(payload), handle, ensure_ascii=False, indent=2)
    os.replace(temporary, target)


def atomic_write_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(rows, key=lambda item: int(item["audio_id"])):
            handle.write(json.dumps(json_safe(row), ensure_ascii=False) + "\n")
    os.replace(temporary, target)


def retry_call(
    operation: Callable[[], Any],
    *,
    attempts: int,
    base_delay_seconds: float,
    retry_if: Callable[[Any], bool] | None = None,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            result = operation()
            if retry_if is None or not retry_if(result):
                return result
            last_error = RuntimeError("Operation returned a retryable result")
        except Exception as exc:
            last_error = exc
        if attempt + 1 < attempts:
            delay = base_delay_seconds * (2**attempt) + random.random() * 0.25
            time.sleep(delay)
    assert last_error is not None
    raise last_error
