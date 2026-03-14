from fastapi import APIRouter
import re
from app.schemas.chat import ChatRequest, ChatResponse
from app.rag.rag_service import retrieve_context
from app.services.llm_service import generate_answer, rewrite_query 
from app.prompts.exam_support import SYSTEM_PROMPT
from app.rag.retriever import get_page_image 

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    image_description = ""
    query_text = req.message if req.message else ""
    
    # BƯỚC 1: Xử lý hình ảnh (Vision OCR) để lấy mã lỗi
    if req.image:
        vision_extraction_prompt = (
            "Chỉ trích xuất mã lỗi hoặc thông báo lỗi ngắn gọn xuất hiện trong ảnh. "
            "Nếu không thấy chữ rõ ràng, hãy trả về 'None'."
        )
        image_description = generate_answer(vision_extraction_prompt, image_base64=req.image)
        if image_description.lower() != "none":
            # Gộp mã lỗi vào query để RAG tìm kiếm chính xác hơn
            query_text = f"{query_text} {image_description}".strip()

    if not query_text:
        return ChatResponse(answer="Vui lòng nhập câu hỏi hoặc gửi ảnh lỗi để tôi hỗ trợ.", page_images=[])

    # BƯỚC 2: Tối ưu hóa truy vấn (LLM Correct Input)
    # Rewrite giúp phân loại đúng Intent (ví dụ: Reset Pass vs Forget Wifi)
    optimized_query = rewrite_query(req.message, image_description)
    print(f"🔍 Optimized Query: {optimized_query}")

    # BƯỚC 3: Truy xuất tài liệu (RAG)
    # retrieve_context trả về context (chuỗi) và source_docs (danh sách dict)
    context, source_docs = retrieve_context(optimized_query)

    if not context:
        return ChatResponse(answer="Tài liệu không có thông tin về vấn đề này. Bạn vui lòng liên hệ giám thị.", page_images=[])

    # BƯỚC 4: Xây dựng Final Prompt cho LLM
    final_prompt = f"""
{SYSTEM_PROMPT}

[DỮ LIỆU ĐẦU VÀO]
- Mô tả lỗi từ ảnh (OCR): {image_description if image_description else "Không có"}
- Câu hỏi gốc của sinh viên: {req.message if req.message else "Sinh viên gửi ảnh lỗi."}

[TÀI LIỆU HƯỚNG DẪN LIÊN QUAN]
{context}

[YÊU CẦU QUAN TRỌNG VỀ TRÍCH DẪN]
Bạn chỉ được hướng dẫn dựa trên thông tin có trong tài liệu. 
Khi kết thúc một hướng dẫn hoặc quy trình, bạn PHẢI trích dẫn nguồn theo đúng định dạng:
[SOURCE: tên_file_pdf, PAGE: số_trang]
Chỉ trích dẫn những trang thực sự cần thiết cho câu trả lời.
"""

    # BƯỚC 5: Gọi LLM tạo câu trả lời cuối cùng
    answer = generate_answer(final_prompt, image_base64=req.image)

    # BƯỚC 6: Trích xuất ảnh dựa trên trích dẫn của LLM
    page_images_data = []
    seen_references = set() 
    
    # Regex để bắt tag: [SOURCE: ..., PAGE: ...]
    pattern = r"\[SOURCE:\s*(.*?),\s*PAGE:\s*(\d+)\]"
    matches = re.findall(pattern, answer, re.IGNORECASE)

    # Lọc danh sách file hợp lệ từ RAG để tránh KeyError và trích dẫn sai
    valid_files = set()
    for doc in source_docs:
        # Kiểm tra cả 2 key 'source' hoặc 'file_name' để đảm bảo không bị KeyError
        f_name = doc.get('source') or doc.get('file_name')
        if f_name:
            valid_files.add(f_name)

    for file_name, page_num in matches:
        file_name = file_name.strip()
        try:
            page_num = int(page_num.strip())
        except ValueError:
            continue
        
        # CHỈ trích xuất ảnh nếu file nằm trong danh sách RAG đã tìm thấy (valid_files)
        if file_name in valid_files:
            ref_key = f"{file_name}_{page_num}"
            if ref_key not in seen_references:
                # Gọi hàm lấy ảnh thực tế từ PDF
                img_b64 = get_page_image(file_name, page_num)
                if img_b64:
                    page_images_data.append({
                        "page": page_num,
                        "file_name": file_name,
                        "base64": img_b64
                    })
                    seen_references.add(ref_key)
        else:
            print(f"🚫 Chặn trích dẫn file không liên quan: {file_name}")

    # Xóa tag trích dẫn khỏi câu trả lời để hiển thị cho người dùng sạch sẽ
    clean_answer = re.sub(pattern, "", answer, flags=re.IGNORECASE).strip()

    return ChatResponse(
        answer=clean_answer,
        page_images=page_images_data
    )