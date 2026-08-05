# app/rag/parser.py
import logging
import pdfplumber
import os

logger = logging.getLogger(__name__)

def load_pdf(path: str):
    """
    Cải tiến: Hỗ trợ nhận vào cả đường dẫn thư mục hoặc file đơn lẻ.
    Lưu lại metadata 'source' để phục vụ việc lọc trùng và trích dẫn.
    """
    documents = []
    
    # Kiểm tra xem path là thư mục hay file đơn lẻ
    if os.path.isdir(path):
        pdf_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.pdf')]
    else:
        pdf_files = [path]

    for pdf_path in pdf_files:
        file_name = os.path.basename(pdf_path)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
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
