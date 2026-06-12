from pydantic import BaseModel
from typing import Optional, List

class PageImage(BaseModel):
    """Cấu trúc dữ liệu cho từng trang ảnh hướng dẫn trích xuất từ PDF"""
    page: int
    file_name: str  # ✅ MỚI: Thêm tên file để phân biệt giữa các tài liệu
    base64: str

class ChatRequest(BaseModel):
    message: str
    image: Optional[str] = None 
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    page_images: Optional[List[PageImage]] = []
    session_id: Optional[str] = None
    session_title: Optional[str] = None
    chat_log_id: Optional[str] = None