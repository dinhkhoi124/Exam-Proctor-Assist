from fastapi import APIRouter, Depends, HTTPException
import re
from sqlalchemy.orm import Session
from datetime import datetime
import time

from app.schemas.chat import ChatRequest, ChatResponse
from app.rag.rag_service import retrieve_context
from app.services.llm_service import generate_answer, rewrite_query
from app.prompts.exam_support import SYSTEM_PROMPT
from app.rag.retriever import get_page_image

from app.db.deps import get_db
from app.models.chat_log import ChatLog
from app.models.chat_session import ChatSession
from app.models.user import User
from app.services.auth_service import get_current_user_from_token
from app.core.websocket import manager

from app.services.logging_service import log_user_activity, save_chat_log
from app.services.topic_service import classify_topic

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
    # RESOLVE CHAT SESSION
    # =========================
    session_id = None
    session_title = None

    if req.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == req.session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.is_deleted == False
        ).first()
        if not session:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        session_id = session.id
        session_title = session.title
        session.updated_at = datetime.utcnow()
        db.commit()
    else:
        # Auto-create session on the first message
        title_text = req.message if req.message else "Ảnh lỗi kỹ thuật"
        title = title_text[:40] + "..." if len(title_text) > 40 else title_text
        session = ChatSession(
            user_id=current_user.id,
            title=title
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
        session_title = session.title

    # =========================
    # XỬ LÝ HÌNH ẢNH (VISION OCR)
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
            # Gộp mã lỗi vào query
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
    # TỐI ƯU HÓA TRUY VẤN (REWRITE QUERY)
    # =========================
    optimized_query = rewrite_query(req.message, image_description)
    print(f"🔍 Optimized Query: {optimized_query}")

    # =========================
    # RAG RETRIEVAL
    # =========================
    context, source_docs = retrieve_context(optimized_query)

    if not context:
        return ChatResponse(
            answer="Tài liệu không có thông tin về vấn đề này. Bạn vui lòng liên hệ giám thị.",
            page_images=[]
        )

    # Lọc danh sách file hợp lệ từ RAG
    valid_files = set()
    for doc in source_docs:
        f_name = doc.get('source') or doc.get('file_name')
        if f_name:
            valid_files.add(f_name)

    # =========================
    # BUILD STRICT PROMPT
    # =========================
    final_prompt = f"""
{SYSTEM_PROMPT}

[DỮ LIỆU ĐẦU VÀO]
- Mô tả lỗi từ ảnh (OCR): {image_description if image_description else "Không có"}
- Câu hỏi gốc của Giám thị: {req.message if req.message else "Giám thị gửi ảnh lỗi."}

[TÀI LIỆU HƯỚNG DẪN LIÊN QUAN]
{context}

[YÊU CẦU QUAN TRỌNG VỀ TRÍCH DẪN]
Bạn chỉ được hướng dẫn dựa trên thông tin có trong tài liệu. 
Khi kết thúc một hướng dẫn hoặc quy trình, bạn PHẢI trích dẫn nguồn theo đúng định dạng:
[SOURCE: tên_file_pdf, PAGE: số_trang]
Chỉ trích dẫn những trang thực sự cần thiết cho câu trả lời.
"""

    # =========================
    # CALL LLM
    # =========================
    start_time = time.time()
    answer = generate_answer(final_prompt, image_base64=req.image)
    latency = int((time.time() - start_time) * 1000)

    # =========================
    # CÁC BƯỚC HẬU KỲ & TRÍCH XUẤT ẢNH
    # =========================
    page_images_data = []
    seen_references = set()

    pattern = r"\[SOURCE:\s*(.*?),\s*PAGE:\s*(\d+)\]"
    matches = re.findall(pattern, answer, re.IGNORECASE)

    for file_name, page_num in matches:
        file_name = file_name.strip()
        try:
            page_num = int(page_num.strip())
        except ValueError:
            continue
        
        # Chỉ xử lý nếu file thực sự thuộc kết quả RAG trả về
        if file_name in valid_files:
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
        else:
            print(f"🚫 Chặn trích dẫn file không liên quan: {file_name}")

    # Làm sạch chuỗi trả lời
    clean_answer = re.sub(pattern, "", answer, flags=re.IGNORECASE).strip()

    # Determine Top Topic
    topic_name = classify_topic(req.message if req.message else image_description)

    # =========================
    # SAVE CHAT LOG TO DB
    # =========================
    chat_log = save_chat_log(
        db=db,
        user_id=current_user.id,
        question=req.message if req.message else image_description,
        answer=clean_answer,
        topic_name=topic_name,
        latency=latency,
        session_id=session_id
    )

    log_user_activity(db, current_user.id, "chat")

    # Trigger admin dashboard update
    await manager.broadcast({"type": "STATS_UPDATED"})
    await manager.broadcast({"type": "CHAT_LOG_CREATED"})

    return ChatResponse(
        answer=clean_answer,
        page_images=page_images_data,
        session_id=str(session_id),
        session_title=session_title,
        chat_log_id=str(chat_log.id) if chat_log else None
    )