import os
import shutil
from app.rag.parser import load_pdf
from app.rag.chunker import semantic_chunk
from app.rag.embedder import VectorStore
from app.core.config import RAG_DATA_DIR, VECTOR_STORE_DIR

def build_vector_store():
    print("🚀 [BUILD INDEX] Bắt đầu quá trình xây dựng lại toàn bộ Index...")

    # 1. Thu thập dữ liệu từ PDF
    raw_docs = load_pdf(RAG_DATA_DIR)
    if not raw_docs:
        print("⚠ Không tìm thấy dữ liệu PDF nào trong thư mục data.")
        return

    # 2. Chia nhỏ văn bản (Sử dụng chunker có overlap để giữ ngữ cảnh)
    chunks = semantic_chunk(raw_docs)
    print(f"📦 Tổng cộng: {len(chunks)} chunks từ các file PDF.")

    # 3. Chuẩn bị dữ liệu cho Embedder
    texts = []
    metas = []

    for c in chunks:
        texts.append(c["text"])
        # PHẲNG HÓA METADATA: Để retriever.py và rag_service.py dễ truy cập
        metas.append({
            "text": c["text"], 
            "page": c["page"], 
            "source": c["source"],
            "metadata": {  # Vẫn giữ bản backup metadata lồng nếu cần
                "source": c["source"], 
                "page": c["page"]
            }
        })

    # 4. Khởi tạo Embedder (Multilingual-E5-Base: 768 dim)
    store = VectorStore(dim=768)

    # 5. Xóa sạch Vector Store cũ (BẮT BUỘC ĐỂ KHÔNG BỊ TRÙNG DỮ LIỆU CŨ)
    if os.path.exists(VECTOR_STORE_DIR):
        try:
            shutil.rmtree(VECTOR_STORE_DIR)
            print("🗑 Đã xóa sạch Vector Store cũ để làm mới hoàn toàn.")
        except Exception as e:
            print(f"⚠ Lỗi khi xóa thư mục cũ: {e}")
    
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    # 6. Tạo Embedding và lưu lại
    print(f"🧠 Đang tạo Embedding (E5 Model)... Bước này có thể mất vài phút.")
    store.add(texts, metas)
    store.save(VECTOR_STORE_DIR)

    print(f"✅ HOÀN TẤT: Đã xây dựng lại Vector Store tại: {VECTOR_STORE_DIR}")

if __name__ == "__main__":
    build_vector_store()