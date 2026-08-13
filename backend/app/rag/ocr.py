"""Optional CPU PaddleOCR adapter used only during document ingestion."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

from app.core.config import RAG_CHUNKS_DIR


logger = logging.getLogger(__name__)
OCR_CACHE_DIR = os.path.join(RAG_CHUNKS_DIR, "ocr_cache")
_pipeline = None
_unavailable_reason: str | None = None


def _detection_model_name() -> str:
    return os.getenv("RAG_OCR_DETECTION_MODEL", "PP-OCRv6_tiny_det")


def _recognition_model_name() -> str:
    return os.getenv("RAG_OCR_RECOGNITION_MODEL", "PP-OCRv6_tiny_rec")


def paddleocr_available() -> bool:
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        return False
    return True


def _get_pipeline():
    global _pipeline, _unavailable_reason
    if _pipeline is not None:
        return _pipeline
    if _unavailable_reason:
        return None
    try:
        from paddleocr import PaddleOCR

        cpu_threads = max(1, int(os.getenv("RAG_OCR_CPU_THREADS", "6")))
        default_mkldnn = "false" if os.name == "nt" else "true"
        enable_mkldnn = os.getenv(
            "RAG_OCR_ENABLE_MKLDNN", default_mkldnn
        ).lower() in {"1", "true", "yes"}
        _pipeline = PaddleOCR(
            device="cpu",
            enable_mkldnn=enable_mkldnn,
            cpu_threads=cpu_threads,
            text_detection_model_name=_detection_model_name(),
            text_recognition_model_name=_recognition_model_name(),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    except Exception as exc:
        _unavailable_reason = str(exc)
        logger.warning("PaddleOCR is unavailable; continuing with PDF text only: %s", exc)
    return _pipeline


def _collect_text(payload, minimum_confidence: float) -> list[str]:
    output = []
    if isinstance(payload, dict):
        texts = payload.get("rec_texts")
        scores = payload.get("rec_scores") or []
        if isinstance(texts, (list, tuple)):
            for index, text in enumerate(texts):
                score = float(scores[index]) if index < len(scores) else 1.0
                if str(text).strip() and score >= minimum_confidence:
                    output.append(str(text).strip())
        for key, value in payload.items():
            if key not in {"rec_texts", "rec_scores"}:
                output.extend(_collect_text(value, minimum_confidence))
    elif isinstance(payload, (list, tuple)):
        if (
            len(payload) == 2
            and isinstance(payload[0], str)
            and isinstance(payload[1], (int, float))
        ):
            if float(payload[1]) >= minimum_confidence:
                output.append(payload[0].strip())
        else:
            for value in payload:
                output.extend(_collect_text(value, minimum_confidence))
    return output


def _result_payload(result):
    payload = getattr(result, "json", result)
    if callable(payload):
        payload = payload()
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload
    return payload


def normalize_ocr_text(text: str) -> str:
    """Repair conservative, recurring punctuation splits in OCR date tokens."""
    return re.sub(
        r"(?<!\d)(\d{1,2}[./_-]\d{1,2}[./_-])20[./_-](\d{2})(?!\d)",
        r"\g<1>20\2",
        str(text or ""),
    )


def extract_page_text(pdf_path: str, page_number: int) -> str:
    """Render one PDF page and OCR it, caching results by rendered image hash."""
    dpi = max(96, int(os.getenv("RAG_OCR_DPI", "144")))
    minimum_confidence = float(os.getenv("RAG_OCR_MIN_CONFIDENCE", "0.65"))
    with fitz.open(pdf_path) as pdf:
        page = pdf.load_page(page_number - 1)
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
        image_bytes = pixmap.tobytes("png")
    cache_identity = (
        f"{_detection_model_name()}|{_recognition_model_name()}|{dpi}|".encode("utf-8")
        + image_bytes
    )
    cache_key = hashlib.sha256(cache_identity).hexdigest()
    cache_path = Path(OCR_CACHE_DIR) / f"{cache_key}.json"
    try:
        return normalize_ocr_text(
            str(json.loads(cache_path.read_text(encoding="utf-8"))["text"])
        )
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        pass

    pipeline = _get_pipeline()
    if pipeline is None:
        return ""

    image = np.asarray(Image.open(__import__("io").BytesIO(image_bytes)).convert("RGB"))
    try:
        if hasattr(pipeline, "predict"):
            results = pipeline.predict(image)
        else:
            results = pipeline.ocr(image, cls=False)
    except Exception as exc:
        logger.exception("PaddleOCR failed for %s page %s: %s", pdf_path, page_number, exc)
        return ""

    lines = []
    for result in results:
        lines.extend(_collect_text(_result_payload(result), minimum_confidence))
    text = normalize_ocr_text(
        "\n".join(dict.fromkeys(line for line in lines if line)).strip()
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(temporary, cache_path)
    return text
