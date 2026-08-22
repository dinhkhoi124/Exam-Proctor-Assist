# Ghi chú thay đổi OCR và Quick Actions

Ngày cập nhật: 22/08/2026

## 1. Sửa lỗi ảnh không liên quan làm chatbot bịa nội dung

### Hiện tượng

Khi người dùng gửi một ảnh không liên quan đến nghiệp vụ coi thi, chẳng hạn ảnh động vật, Vision LLM vẫn có thể sinh ra mô tả lỗi. Nội dung này trước đây được nối trực tiếp vào truy vấn RAG, khiến hệ thống lấy tài liệu gần nhất và trả lời như thể ảnh thực sự chứa lỗi.

Frontend vẫn sử dụng câu mặc định `Hãy phân tích hình ảnh lỗi này.` khi người dùng chỉ gửi ảnh. Câu này phục vụ hiển thị và mô tả thao tác của người dùng; backend không được xem câu mặc định hoặc lời khẳng định trong chat là bằng chứng rằng ảnh có lỗi.

### Workflow mới

```text
Người dùng gửi ảnh
→ Chuẩn hóa và kiểm tra dữ liệu ảnh Base64
→ Vision phân loại ảnh và OCR nội dung lỗi
→ Parse kết quả JSON theo cơ chế fail-closed
→ Không có mã/thông báo lỗi rõ ràng: dừng trước RAG
→ Có lỗi rõ ràng: kết hợp câu hỏi và nội dung OCR để truy vấn RAG
→ Sinh câu trả lời chỉ từ evidence tìm được
```

Nếu request có ảnh nhưng ảnh không cung cấp bằng chứng lỗi hợp lệ, backend tạo query rỗng và trả về:

> Không phát hiện mã hoặc thông báo lỗi rõ ràng trong ảnh, nên không tìm thấy thông tin tương ứng trong tài liệu. Vui lòng gửi ảnh chụp màn hình lỗi rõ hơn.

Quy tắc này vẫn áp dụng khi phần chat ghi những câu như `Sinh viên gặp lỗi trong ảnh`. Nội dung chat không được dùng để bỏ qua kết quả OCR của ảnh.

### Cấu trúc kết quả Vision

Vision được yêu cầu chỉ trả về một trong hai dạng JSON:

```json
{"relevant": false, "error_text": ""}
```

hoặc:

```json
{"relevant": true, "error_text": "nguyên văn mã hoặc thông báo lỗi nhìn thấy rõ"}
```

Các trường hợp sau bị loại và không được đưa vào RAG:

- Ảnh đời thường, động vật, phong cảnh, người, meme hoặc đồ vật thông thường.
- Không có mã hoặc thông báo lỗi nghiệp vụ rõ ràng.
- Vision trả văn bản tự do thay vì JSON.
- JSON sai cấu trúc hoặc dùng giá trị chuỗi `"true"` thay cho boolean `true`.
- `error_text` rỗng hoặc dài quá 500 ký tự.
- Vision cố giải thích, suy đoán hoặc tạo mã lỗi không có bằng chứng hợp lệ.

### Các file liên quan

- `backend/app/services/llm_service.py`
  - Thêm `ImageAnalysis`.
  - Thêm parser JSON fail-closed `_parse_image_analysis_response()`.
  - Thêm `analyze_uploaded_image()` để phân loại và OCR ảnh.
  - Thêm `build_image_aware_query()` để chặn retrieval khi ảnh không có bằng chứng lỗi.
  - Giữ `extract_image_text()` làm wrapper tương thích với caller cũ.
- `backend/app/api/v1/chat.py`
  - Dùng kết quả `ImageAnalysis` thay cho chuỗi OCR tự do.
  - Dừng trước `retrieve_context()` nếu ảnh không có lỗi hợp lệ.
  - Trả thông báo không tìm thấy thông tin tương ứng trong tài liệu.
- `frontend/src/components/chat/ChatInput.tsx`
  - Giữ câu mặc định `Hãy phân tích hình ảnh lỗi này.` khi chỉ gửi ảnh.
- `frontend/src/components/chat/ChatWindow.tsx`
  - Hiển thị đúng câu mặc định trên, không dùng nội dung `Đã gửi một hình ảnh.`.

`backend/app/rag/parser.py` không tham gia xử lý ảnh chat. File này chỉ OCR trang PDF trong quá trình ingest/build index tài liệu RAG.

### Kết quả kiểm tra trước khi chuyển thay đổi sang branch

- Toàn bộ backend: `61 passed`.
- Test riêng xử lý ảnh: `6 passed` (không đưa thư mục test vào commit theo yêu cầu).
- Python compile: thành công.
- Frontend test: `2 passed`.
- Frontend ESLint: thành công.
- Frontend production build: thành công.

## 2. Quick Actions hiện tại

File cấu hình: `frontend/src/components/chat/QuickActions.tsx`.

| Icon | Nhãn hiển thị | Query gửi vào chatbot |
|---|---|---|
| `Wifi` | Sự cố WiFi phòng thi | `Thí sinh không kết nối được WiFi phòng thi` |
| `LogIn` | Kết nối WiFi thi | `Hướng dẫn kết nối wifi phòng thi` |
| `Globe` | Ký tên điện tử | `Hướng dẫn sinh viên ký tên điện tử` |
| `Clock` | Sinh viên đi muộn | `Sinh viên đi muộn` |
| `Download` | Tải EOS | `Hướng dẫn tải EOS` |
| `Laptop` | Sự cố thiết bị | `Máy tính của sinh viên bị treo` |
| `Phone` | Email phòng đào tạo | `Email của phòng đào tạo là gì?` |

Mỗi nút gọi `onSelect(action.query)`. Việc sửa nhãn chỉ thay đổi nội dung hiển thị; việc sửa `query` làm thay đổi câu được gửi đến backend và có thể ảnh hưởng kết quả retrieval RAG.
