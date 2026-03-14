import fitz  # PyMuPDF
import base64
import os
import io
import imagehash
from PIL import Image
from app.core.config import RAG_DATA_DIR

def get_page_image(file_name: str, page_number: int):
    """Trích xuất một trang PDF thành ảnh Base64 chất lượng cao"""
    try:
        pdf_path = os.path.join(RAG_DATA_DIR, file_name)
        if not os.path.exists(pdf_path):
            return None

        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1) 
        # Matrix 2 để ảnh đủ rõ cho người dùng xem
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("png")
        doc.close() 
        
        return base64.b64encode(img_data).decode("utf-8")
    except Exception as e:
        print(f"Error extracting PDF page: {e}")
        return None

def get_unique_pages(retrieved_results: list):
    """
    Hàm lọc trùng ảnh: Sử dụng Perceptual Hashing với ngưỡng nới lỏng
    để nhận diện Slide và Văn bản có nội dung tương đồng.
    """
    unique_results = []
    seen_hashes = [] # Dùng list để dễ so sánh
    
    # Nâng ngưỡng (Threshold) lên 12-15 để lọc các trang có bố cục hơi khác
    # nhưng nội dung chính (text/ý nghĩa) giống nhau.
    hash_threshold = 15 

    for res in retrieved_results:
        file_name = res.get('source')
        page_num = res.get('page')
        
        if not file_name or not page_num:
            continue

        pdf_path = os.path.join(RAG_DATA_DIR, file_name)
        if not os.path.exists(pdf_path):
            continue

        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num - 1)
            # Dùng matrix thấp để tính hash nhanh
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5)) 
            img_bytes = pix.tobytes("png")
            doc.close()

            # 1. Chuyển đổi và chuẩn hóa ảnh
            img = Image.open(io.BytesIO(img_bytes)).convert("L") # Chuyển về ảnh xám
            img = img.resize((256, 256), Image.Resampling.LANCZOS) # Ép kích thước chuẩn
            
            # 2. Tính toán Perceptual Hash (phash ổn định hơn với thay đổi bố cục)
            current_hash = imagehash.phash(img)

            # 3. Kiểm tra trùng lặp với ngưỡng nới lỏng
            is_duplicate = False
            for h in seen_hashes:
                if current_hash - h <= hash_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # Nếu không trùng, lấy ảnh Base64 chất lượng cao
                res['image_base64'] = get_page_image(file_name, page_num)
                unique_results.append(res)
                seen_hashes.append(current_hash)
            else:
                print(f"📌 Đã chặn trang trùng: {file_name} trang {page_num}")
        
        except Exception as e:
            print(f"Error processing unique page: {e}")
            continue

    return unique_results