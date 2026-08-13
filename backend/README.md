# FPT Exam Support Backend

FastAPI backend cho chatbot RAG hỗ trợ nghiệp vụ coi thi.

## Yêu cầu

- Python 3.12
- uv
- PostgreSQL

## Cài đặt backend

```bash
cp .env.example .env
uv sync
```

Điền kết nối cơ sở dữ liệu và khóa JWT trong `.env` trước khi khởi động.

## Chạy với Qwen cục bộ

Từ thư mục `Chatbot_Module`, chạy model ở terminal riêng:

```bash
./scripts/run_qwen_vllm.sh
```

Script kiểm tra CUDA trước khi load checkpoint. Nếu PyTorch báo CUDA không khả
dụng và `nvidia-smi -q -i 0` hiển thị `GPU requires reset`, cần reboot máy rồi
chạy lại; thay đổi tham số vLLM hoặc giảm VRAM không sửa được trạng thái driver
này.

Script phục vụ checkpoint `qwen3-vl-4b-it-finetuned_v3` qua API tương thích
OpenAI tại `http://127.0.0.1:8001/v1`, với tên model
`qwen3-exam-assist`. Model này được dùng cho trả lời và vision OCR. Query
retrieval được chuẩn hóa bằng luật để giữ nguyên mã lỗi/thuật ngữ và không gọi
Qwen rewrite trên hot path. Có thể kiểm tra service bằng:

```bash
curl http://127.0.0.1:8001/v1/models
```

Sau đó chạy backend ở terminal khác:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On Windows PowerShell, if `uv` is not available in `PATH`, run Uvicorn with
the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Các biến tương ứng trong `.env`:

```dotenv
LLM_BASE_URL=http://127.0.0.1:8001/v1
LLM_API_KEY=local
LLM_MODEL=qwen3-exam-assist
QUERY_REWRITE_MODEL=qwen3-exam-assist
VISION_BASE_URL=http://127.0.0.1:8001/v1
VISION_API_KEY=local
VISION_MODEL=qwen3-exam-assist
EMBEDDING_DEVICE=cpu
EMBEDDING_LOCAL_FILES_ONLY=true
```

E5 vẫn là `intfloat/multilingual-e5-base`, nhưng mặc định chạy trên CPU để
không tranh VRAM với Qwen. MiniLM cross-encoder cũ đã được bỏ vì không tham gia
hiệu quả vào pipeline retrieval hiện tại.

## Chuyển lại OpenAI

Không cần sửa code. Đổi các biến model trong `.env`:

```dotenv
LLM_BASE_URL=
LLM_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
QUERY_REWRITE_MODEL=gpt-4o-mini
VISION_BASE_URL=
VISION_API_KEY=your-openai-api-key
VISION_MODEL=gpt-4o-mini
```

`OPENAI_API_KEY` hiện chỉ còn cần cho STT/TTS OpenAI cũ. Backend vẫn khởi động
được khi không có khóa này nếu LLM local đã được cấu hình.

## Faster-Whisper (CTranslate2)

Model `Systran/faster-whisper-medium` sẽ tự tải về ở lần khởi động đầu tiên, tại:

```text
../models/faster-whisper-medium
```

Từ thư mục `Chatbot_Module`, chạy CPU ASR ở terminal riêng:

```bash
./scripts/run_faster_whisper_cpu.sh
```

Service tương thích OpenAI chạy tại `http://127.0.0.1:8002/v1`. Script chạy CTranslate2 CPU `int8`, dùng 16 CPU thread và đúng một worker/model instance. WebRTC VAD được chạy trước; audio im lặng trả về chuỗi rỗng và không làm model được load. Request có giọng nói được xếp hàng với concurrency inference bằng 1.

Kiểm tra service:

```bash
curl http://127.0.0.1:8002/health
```

Backend dùng service qua các biến:

```dotenv
STT_BASE_URL=http://127.0.0.1:8002/v1
STT_API_KEY=local
STT_MODEL=faster-whisper-medium
STT_FALLBACK_MODEL=
STT_TIMEOUT_SECONDS=180
STT_LANGUAGE=
```

Model lazy-load ở request có giọng nói đầu tiên, nên lần nhận dạng đầu sẽ chậm
hơn các lần sau. Để quay lại OpenAI STT, để trống `STT_BASE_URL`, đặt API key,
model và fallback tương ứng.

## Dữ liệu RAG

- Tài liệu nguồn: `app/rag/data/`
- Chỉ mục tìm kiếm: `app/rag/vector_store/`
- Tạo lại chỉ mục: `uv run python -m app.rag.build_index`

Trên Windows PowerShell không có `uv`, dùng:

```powershell
.\.venv\Scripts\python.exe -m app.rag.build_index
```

Pipeline retrieval hiện tại:

```text
Query/OCR chuẩn hóa
→ BM25 top 30 + multilingual-E5-base top 30
→ Weighted RRF (k=60, 0.5/0.5)
→ exact/heading/intent boost có giới hạn
→ gom child về parent
→ dedup văn bản
→ confidence gate
→ tối đa 5 evidence parent
→ Qwen trả lời và trích evidence ID
→ ảnh minh họa chỉ lấy từ một PDF nguồn chính theo tổng điểm evidence được trích dẫn
```

E5 vẫn chạy trên CPU. Child được giới hạn khoảng 380 ký tự, overlap 70 ký tự;
parent nằm trong một trang PDF và tối đa khoảng 1.200 ký tự để giữ trích dẫn
trang chính xác. Có thể hiệu chỉnh confidence gate bằng
`RAG_MIN_DENSE_SCORE` và `RAG_MIN_BM25_SCORE`.

### Temporal discovery và OCR CPU

Mỗi lần upload, xóa hoặc chạy `build_index`, backend tự phát hiện family/ngày
phiên bản từ tên file và nội dung trang, tự tính lại `version_rank`, rồi ghi bản
chẩn đoán vào `app/rag/temporal_manifest.generated.json`. Quy trình này không gọi
LLM. `temporal_manifest.json` chỉ còn là lớp override cho dữ liệu đã xác minh và
không cần cập nhật đối với tài liệu thông thường.

Trang có ảnh lớn, có dấu hiệu phiên bản/phát hành/tải về nhưng text layer không
chứa ngày sẽ được xử lý bằng PP-OCRv6-tiny trên CPU. Kết quả được cache theo ảnh,
model và DPI tại
`app/rag/chunks/ocr_cache/`; tài liệu không thay đổi sẽ không bị OCR lại.

Nếu máy không có `uv`, cài OCR trong virtual environment bằng PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install "paddleocr>=3.3,<4" "paddlepaddle>=3.2,<4"
```

Nếu PaddleOCR không được cài hoặc gặp lỗi, build vẫn tiếp tục bằng text layer của
PDF và không loại bỏ tài liệu.

Document family không còn được khai báo theo danh sách EOS/E360/USB cố định.
Backend chuẩn hóa tên file, bỏ ngày/version noise, suy ra subtype tổng quát và
đối chiếu tập từ nội dung để tạo family fingerprint. Clustering dùng complete-link
để một tài liệu tên chung không thể nối bắc cầu và trộn hai family khác nhau.
Family có ít nhất hai tài liệu có ngày và confidence đủ cao mới được đánh dấu
`verified`; singleton hoặc nhóm mơ hồ là `provisional` và không điều khiển latest.
`temporal_manifest.json` chỉ giữ page override đã xác minh, không còn document
family thủ công.

### Đồng bộ PDF với database

`build_index` không chỉ tạo lại vector index. Sau khi build thành công, nó còn
upsert toàn bộ PDF hiện có trong `app/rag/data` vào bảng tài liệu RAG, đồng thời
loại bản ghi không còn file tương ứng. Luồng upload/xóa từ UI sử dụng cùng cơ chế
đồng bộ, vì vậy không cần xóa và nạp lại một file để kích hoạt đồng bộ cho các PDF
khác.

### Trích dẫn ảnh cho hướng dẫn nhiều bước

Backend gom ảnh theo một PDF nguồn chính, chuẩn hóa tiêu đề/section, nhận diện các
marker `Bước N`, sắp theo thứ tự bước rồi khử trùng lặp theo trang và nội dung.
Các trang quy trình liền kề được bổ sung trong giới hạn an toàn khi evidence text
chứng minh cùng section. Việc này giữ ảnh đúng thứ tự, hạn chế thiếu bước và không
trộn các phần hướng dẫn khác nhau.

### Kiểm tra sau khi thay đổi RAG

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m app.rag.build_index
python -m uvicorn app.main:app --reload
```

Chỉ cần build lại index khi PDF, parser, chunk metadata, embedding hoặc logic
temporal thay đổi. Chỉ khởi động lại backend nếu thay đổi code truy vấn/trả lời.
