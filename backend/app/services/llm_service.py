# app/services/llm_service.py
from openai import OpenAI
import os
from app.prompts.exam_support import SYSTEM_PROMPT 

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def rewrite_query(user_input: str, image_ocr: str = None) -> str:
    rewrite_prompt = f"""
    Bạn là chuyên gia điều phối dữ liệu RAG. 
    Nhiệm vụ: Tạo ra một Search Query ĐƠN NHẤT và CHÍNH XÁC NHẤT.

    [NGỮ CẢNH]
    - Nếu có lỗi từ ảnh: {image_ocr if image_ocr else "Không"} 
    - Câu hỏi SV: {user_input}

    [CHIẾN LƯỢC TÌM KIẾM]
    1. Nếu có lỗi từ ảnh: Ưu tiên tìm kiếm các tài liệu liên quan đến mã lỗi đó.
    2. Ưu tiên tìm các ảnh tài liệu hướng dẫn liên quan đến câu trả lời.
    3. Nếu SV hỏi về mật khẩu: CHỈ tìm 'hướng dẫn đổi mật khẩu wifi portal'.
    4. TUYỆT ĐỐI không trộn lẫn các từ khóa 'wifi', 'mạng', 'vpn' nếu mục tiêu là 'mật khẩu'.

    Trả về DUY NHẤT search query:"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": rewrite_prompt}],
        temperature=0
    )
    
    return response.choices[0].message.content.strip()

def generate_answer(prompt: str, image_base64: str = None):
    """
    Hàm sinh câu trả lời cuối cùng từ Context và ảnh.
    """
    messages = [
        {
            "role": "system", 
            "content": SYSTEM_PROMPT
        }
    ]
    
    user_content = [{"type": "text", "text": prompt}]
    
    if image_base64:
        clean_base64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{clean_base64}"
            }
        })
    
    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1 
    )

    return response.choices[0].message.content.strip()