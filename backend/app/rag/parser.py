# app/rag/parser.py
import logging
import pdfplumber
import os
import re

from app.rag.ocr import extract_page_text

logger = logging.getLogger(__name__)


_DATE_PATTERN = re.compile(
    r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[./_-](?:0?[1-9]|1[0-2])"
    r"[./_-](?:20\d{2}|\d{2})(?!\d)"
)


def _image_area_ratio(page) -> float:
    page_area = float(page.width * page.height) or 1.0
    image_area = 0.0
    for image in page.images:
        width = max(float(image.get("x1", 0)) - float(image.get("x0", 0)), 0.0)
        height = max(float(image.get("bottom", 0)) - float(image.get("top", 0)), 0.0)
        image_area += width * height
    return min(image_area / page_area, 1.0)


def _should_ocr(page, text: str, source: str) -> bool:
    if os.getenv("RAG_OCR_ENABLED", "true").lower() not in {"1", "true", "yes"}:
        return False
    if not page.images:
        return False
    normalized = text.casefold()
    if not text.strip():
        return os.getenv("RAG_OCR_SCAN_EMPTY_PAGES", "false").lower() in {
            "1", "true", "yes"
        }
    # Generic release/download cues decide whether an image-rich page may hide
    # version metadata. Product names are deliberately not listed here.
    release_markers = (
        "phiên bản", "phien ban", "version", "release", "cập nhật", "cap nhat",
        "download", "tải phần mềm", "tai phan mem", "gói cài đặt", "goi cai dat",
        "installer", "client", "software",
    )
    return (
        any(marker in normalized for marker in release_markers)
        and _image_area_ratio(page) >= float(os.getenv("RAG_OCR_MIN_IMAGE_RATIO", "0.25"))
        and not _DATE_PATTERN.search(text)
    )

def load_pdf(path: str):
    """
    Cải tiến: Hỗ trợ nhận vào cả đường dẫn thư mục hoặc file đơn lẻ.
    Lưu lại metadata 'source' để phục vụ việc lọc trùng và trích dẫn.
    """
    documents = []
    
    # Kiểm tra xem path là thư mục hay file đơn lẻ
    if os.path.isdir(path):
        pdf_files = [
            os.path.join(path, file_name)
            for file_name in os.listdir(path)
            if file_name.lower().endswith(".pdf")
        ]
    else:
        pdf_files = [path]

    for pdf_path in pdf_files:
        file_name = os.path.basename(pdf_path)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if _should_ocr(page, text, file_name):
                        try:
                            ocr_text = extract_page_text(pdf_path, i + 1)
                        except Exception:
                            logger.exception(
                                "OCR failed for %s page %s; using PDF text layer",
                                file_name,
                                i + 1,
                            )
                            ocr_text = ""
                        if ocr_text and ocr_text not in text:
                            text = f"{text}\n[OCR]\n{ocr_text}".strip()
                    if not text:
                        continue

                    cleaned = (
                        text.replace("\u00a0", " ")
                            .replace("\n\n", "\n")
                            .strip()
                    )

                    documents.append({
                        "content": cleaned,
                        "page": i + 1,
                        "source": file_name  # Lưu tên file để retriever.py sử dụng
                    })
        except Exception:
            logger.exception("Failed to parse PDF file %s", file_name)

    return documents
