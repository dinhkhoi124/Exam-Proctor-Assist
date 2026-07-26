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
