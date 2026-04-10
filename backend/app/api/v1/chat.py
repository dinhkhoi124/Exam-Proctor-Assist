from fastapi import APIRouter, Depends
import re
from sqlalchemy.orm import Session
from datetime import datetime

from app.schemas.chat import ChatRequest, ChatResponse
from app.rag.rag_service import retrieve_context
from app.services.llm_service import generate_answer
from app.prompts.exam_support import SYSTEM_PROMPT
from app.rag.retriever import get_page_image

from app.db.deps import get_db
from app.models.chat_log import ChatLog
from app.models.user import User
from app.services.auth_service import get_current_user_from_token

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    image_description = ""
    query_text = req.message if req.message else ""

    # =========================
    # UPDATE LAST ACTIVE
    # =========================
    current_user.last_active = datetime.utcnow()

    # =========================
    # XỬ LÝ HÌNH ẢNH
    # =========================
    if req.image:
        vision_extraction_prompt = (
            "Chỉ trích xuất mã lỗi hoặc thông báo lỗi ngắn gọn xuất hiện trong ảnh. "
            "Nếu không thấy chữ rõ ràng, hãy trả về 'None'."
        )
        image_description = generate_answer(
            vision_extraction_prompt,
            image_base64=req.image
        )

        if image_description.lower() != "none":
            query_text = f"{query_text} {image_description}".strip()

    # =========================
    # VALIDATE INPUT
    # =========================
    if not query_text:
        return ChatResponse(
            answer="Vui lòng nhập câu hỏi hoặc gửi ảnh lỗi để tôi hỗ trợ.",
            page_images=[]
        )

    # =========================
    # SAVE CHAT LOG
    # =========================
    chat_log = ChatLog(
    user_id=current_user.id,
    question=req.message if req.message else image_description
)

    db.add(chat_log)
    db.commit()

    # =========================
    # RAG RETRIEVAL
    # =========================
    context, source_docs = retrieve_context(query_text)

    if not context:
        return ChatResponse(
            answer="Tài liệu không có thông tin về vấn đề này. Bạn vui lòng liên hệ giám thị.",
            page_images=[]
        )

    # =========================
    # BUILD PROMPT
    # =========================
    final_prompt = f"""
{SYSTEM_PROMPT}

[DỮ LIỆU ĐẦU VÀO]
- Mô tả lỗi từ ảnh (OCR): {image_description if image_description else "Không có"}
- Câu hỏi của sinh viên: {req.message if req.message else "Sinh viên gửi ảnh lỗi."}

[TÀI LIỆU HƯỚNG DẪN LIÊN QUAN]
{context}

[YÊU CẦU QUAN TRỌNG VỀ TRÍCH DẪN]
Khi hướng dẫn, bạn PHẢI trích dẫn nguồn bằng định dạng chính xác sau ở cuối câu trả lời nếu có thông tin liên quan:
[SOURCE: tên_file_pdf, PAGE: số_trang]
Ví dụ: [SOURCE: HDSD HT E360_31.12.25.pdf, PAGE: 5]
"""

    # =========================
    # CALL LLM
    # =========================
    answer = generate_answer(final_prompt, image_base64=req.image)

    # =========================
    # EXTRACT PAGE IMAGES
    # =========================
    page_images_data = []
    seen_references = set()

    pattern = r"\[SOURCE:\s*(.*?),\s*PAGE:\s*(\d+)\]"
    matches = re.findall(pattern, answer, re.IGNORECASE)

    for file_name, page_num in matches:
        file_name = file_name.strip()
        page_num = int(page_num.strip())
        ref_key = f"{file_name}_{page_num}"

        if ref_key not in seen_references:
            img_b64 = get_page_image(file_name, page_num)

            if img_b64:
                page_images_data.append({
                    "page": page_num,
                    "file_name": file_name,
                    "base64": img_b64
                })
                seen_references.add(ref_key)

    # =========================
    # CLEAN ANSWER
    # =========================
    clean_answer = re.sub(pattern, "", answer, flags=re.IGNORECASE).strip()

    # =========================
    # UPDATE CHAT LOG WITH ANSWER
    # =========================
    chat_log.answer = clean_answer
    db.commit()

    return ChatResponse(
        answer=clean_answer,
        page_images=page_images_data
    )