import os
from collections import Counter
from app.core.config import VECTOR_STORE_DIR
from app.rag.embedder import VectorStore 
from app.rag.retriever import get_unique_pages 

_store = VectorStore(dim=768)

def load_resources():
    global _store
    if os.path.exists(os.path.join(VECTOR_STORE_DIR, "index.faiss")):
        _store.load(VECTOR_STORE_DIR)

load_resources()

def retrieve_context(query: str, top_k: int = 15): # Tăng top_k thô lên cao để bao quát nhiều file
    if not _store.metadata:
        return "Hệ thống đang cập nhật...", []

    # 1. Search lấy danh sách thô rộng
    raw_results = _store.search(query, top_k=top_k)
    
    # 2. PHÂN TÍCH NGUỒN (Source Analysis)
    # Tìm xem file nào xuất hiện nhiều nhất và có điểm tương đồng cao nhất
    source_counts = Counter([res.get('source') for res in raw_results if res.get('source')])
    if not source_counts:
        return "Không tìm thấy tài liệu phù hợp.", []
    
    # Lấy file "chuyên biệt" nhất (xuất hiện nhiều nhất trong top results)
    best_source = source_counts.most_common(1)[0][0]
    
    # 3. LỌC CỨNG (Strict Filtering): Chỉ giữ lại kết quả từ file tốt nhất 
    # Nếu file tốt nhất chiếm ưu thế (ví dụ > 30% kết quả search)
    filtered_results = []
    for res in raw_results:
        if res.get('source') == best_source:
            filtered_results.append(res)
    
    # Nếu file chuyên biệt quá ít thông tin, mới bổ sung từ file khác (optional)
    if len(filtered_results) < 3:
        for res in raw_results:
            if res.get('source') != best_source:
                filtered_results.append(res)
            if len(filtered_results) >= 6: break

    # 4. SẮP XẾP THEO THỨ TỰ TRANG (Tránh mất bước)
    # Cực kỳ quan trọng cho "hướng dẫn": Sắp xếp lại để Bước 1 đến trước Bước 2
    filtered_results.sort(key=lambda x: x.get('page', 0))

    # 5. Lọc trùng ID trang và Hình ảnh như trước
    seen_page_ids = set()
    final_to_process = []
    for res in filtered_results:
        page_id = f"{res.get('source')}_{res.get('page')}"
        if page_id not in seen_page_ids:
            final_to_process.append({
                "source": res.get('source'),
                "page": res.get('page'),
                "content": res.get('text', '')
            })
            seen_page_ids.add(page_id)

    # 6. Lọc trùng ảnh bằng Hash (threshold 15)
    unique_pages = get_unique_pages(final_to_process)

    # 7. Trả về context (giới hạn 5 trang để đủ các bước hướng dẫn)
    final_pages = unique_pages[:5] 
    context_parts = []
    source_documents = []

    for item in final_pages:
        context_parts.append(f"--- Nguồn: {item['source']} (Trang {item['page']}) ---\n{item['content']}")
        source_documents.append({
            "file_name": item['source'],
            "page": item['page'],
            "image_base64": item.get('image_base64')
        })

    return "\n\n".join(context_parts), source_documents