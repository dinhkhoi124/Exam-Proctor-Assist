from app.rag.parser import load_pdf
from app.rag.chunker import semantic_chunk
from app.rag.embedder import VectorStore
import os

# Sử dụng đường dẫn từ config để đồng nhất với rag_service
from app.core.config import RAG_DATA_DIR, VECTOR_STORE_DIR

# 1. Load PDF
# Đảm bảo load_pdf trả về list các dict có kèm metadata 'source'
docs = load_pdf(RAG_DATA_DIR) 

# 2. Chunking
# Chunker nên giữ lại thông tin source từ doc gốc
chunks = semantic_chunk(docs)

texts = []
metas = []

for c in chunks:
    # Làm sạch text sơ bộ để tránh lưu các khoảng trắng thừa gây nhiễu embedding
    clean_text = c["text"].strip()
    if len(clean_text) < 20: # Loại bỏ các chunk quá ngắn, không có nghĩa
        continue
        
    texts.append(clean_text)
    # QUAN TRỌNG: Phải lưu 'source' để hàm lọc trùng ảnh hoạt động được
    metas.append({
        "text": clean_text, 
        "page": c["page"],
        "source": c.get("source", "unknown.pdf") # Lấy tên file từ parser
    })

# 3. Embedding & Store
store = VectorStore()
store.add(texts, metas)

# Lưu vào thư mục mà rag_service.py đang cấu hình để đọc
if not os.path.exists(VECTOR_STORE_DIR):
    os.makedirs(VECTOR_STORE_DIR)

store.save(VECTOR_STORE_DIR)

print(f"✅ RAG index built successfully với {len(texts)} chunks.")