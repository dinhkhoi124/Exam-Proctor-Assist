# app/rag/chunker.py
import re

def semantic_chunk(documents, max_length=1000, overlap=150):
    """
    Cải tiến: Giữ lại metadata 'source' và thêm cơ chế Overlap để tránh mất ngữ cảnh.
    """
    chunks = []

    for doc in documents:
        text = doc["content"]
        page = doc["page"]
        source = doc.get("source", "unknown.pdf") # Lấy source từ parser truyền sang

        # 1. Tách theo heading / bullet / bước (giữ nguyên logic Regex của bạn)
        # Bổ sung thêm các ký hiệu mục lục phổ biến
        sections = re.split(
            r"\n(?=(?:BƯỚC|LƯU Ý|CHÚ Ý|HƯỚNG DẪN|NOTE|STEP|MỤC|\d+\.|[a-z]\)\s) )",
            text,
            flags=re.IGNORECASE
        )

        buffer = ""
        for sec in sections:
            # Nếu thêm đoạn mới vẫn nhỏ hơn max_length, dồn vào buffer
            if len(buffer) + len(sec) < max_length:
                buffer += "\n" + sec
            else:
                # Lưu chunk hiện tại
                if buffer.strip():
                    chunks.append({
                        "text": buffer.strip(),
                        "page": page,
                        "source": source  # PHẢI CÓ: Để retriever.py biết file nào mà lọc trùng
                    })
                
                # Tạo buffer mới với một phần overlap từ chunk cũ để giữ ngữ cảnh
                buffer = buffer[-overlap:] + "\n" + sec if overlap < len(buffer) else sec

        # Lưu đoạn cuối cùng
        if buffer.strip():
            chunks.append({
                "text": buffer.strip(),
                "page": page,
                "source": source
            })

    return chunks