# Báo cáo so sánh phiên bản cũ và mới

Ngày đối chiếu: 2026-07-26

## Phạm vi và phương pháp

- Backend cũ: `backend/`
- Backend mới: `deploy_packages/backend_new_version/`
- Frontend cũ: `frontend/`
- Frontend mới: `deploy_packages/frontend_new_version/`
- File được ghép cặp theo đường dẫn tương đối và so sánh nội dung bằng SHA-256.
- Không tính các thư mục/file sinh tự động: `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist`, `build`, `coverage`, `.next`, `*.pyc`, `*.pyo`.
- Không đọc hoặc công bố nội dung các file `.env`; báo cáo chỉ ghi nhận trạng thái thay đổi.

## Tổng quan

| Thành phần | File cũ | File mới | Thay đổi | Bổ sung | Bị xoá | Không đổi |
|---|---:|---:|---:|---:|---:|---:|
| Backend | 111 | 118 | 36 | 18 | 11 | 64 |
| Frontend | 118 | 73 | 56 | 9 | 54 | 8 |

PDF `app/rag/data/THI TRÊN USB 13.5.26 - GV.pdf` có mặt ở cả hai backend và đều có kích thước 0 byte, nên được tính là không đổi. Đây vẫn là một vấn đề dữ liệu cần xử lý.

## Đánh giá thay đổi chính

### Backend

- Pipeline RAG được làm lại đáng kể: hybrid BM25 + dense retrieval, weighted RRF, rule boost, gom child/parent chunk, lọc trùng, confidence gate, giới hạn evidence và citation theo mã `E1`, `E2`,...
- Tách client mô hình ra `model_clients.py`, hỗ trợ cấu hình model local/OpenAI-compatible; bổ sung hậu xử lý câu trả lời và chọn nguồn evidence chính.
- Bổ sung voice correction và cập nhật luồng STT/TTS.
- Mở rộng quản trị người dùng/chat: soft delete, thùng rác, khôi phục, xoá vĩnh viễn, retention 30 ngày và tác vụ purge nền.
- Chuẩn hoá timezone Việt Nam/UTC và danh tính email/username không phân biệt hoa thường thông qua ba migration mới.
- Chuyển sang cấu trúc đóng gói bằng `pyproject.toml` + `uv.lock`, có hướng dẫn triển khai và bốn file test mới.
- Các artifact chỉ mục RAG (`index.faiss`, BM25 và metadata) đều đổi; khi triển khai phải giữ chúng đồng bộ với nhau và với tài liệu nguồn.

### Frontend

- Tên package đổi thành `fpt-exam-support-frontend`, version `0.1.0`.
- Loại bỏ nhiều Radix/shadcn component và dependency không còn dùng, giúp source/package gọn hơn.
- Tách contract auth sang `src/context/auth.ts`, bổ sung chuẩn hoá lỗi API.
- Trang quản trị người dùng được mở rộng mạnh, có UI thùng rác cho tài khoản và các đợt xoá chat.
- Logo JPG được thay bằng WebP.
- Cấu hình môi trường chuyển từ `.env.development`/`.env.production` sang `.env` + `.env.example`; bổ sung tài liệu triển khai.

## Các điểm cần lưu ý trước khi triển khai

1. Chạy ba migration backend theo đúng thứ tự `001` → `002` → `003` và sao lưu database trước khi chạy.
2. Kiểm tra/xoá secret khỏi hai file `.env` nằm trong package trước khi chia sẻ hoặc đóng gói. `.gitignore` đã bỏ qua `.env`, nhưng file vật lý vẫn đang tồn tại.
3. Khắc phục PDF 0 byte `THI TRÊN USB 13.5.26 - GV.pdf`, sau đó build lại toàn bộ vector store nếu tài liệu này phải tham gia RAG.
4. Tác vụ purge trong `app/main.py` đang bắt và bỏ qua mọi exception; nên bổ sung logging/monitoring để lỗi purge không bị im lặng.
5. Backend mới có test nhưng môi trường hiện tại chưa cài `pytest`, nên chưa xác nhận được kết quả test. Frontend mới cũng chưa được `npm install/build` trong lần đánh giá này.

## Backend — file đã thay đổi (36)

- `.env`
- `.env.example`
- `app/api/v1/admin.py`
- `app/api/v1/auth.py`
- `app/api/v1/chat.py`
- `app/api/v1/chat_session.py`
- `app/api/v1/feedback.py`
- `app/api/v1/speech.py`
- `app/core/config.py`
- `app/core/websocket.py`
- `app/db/session.py`
- `app/main.py`
- `app/models/chat_log.py`
- `app/models/chat_session.py`
- `app/models/chat_topic.py`
- `app/models/user.py`
- `app/models/user_activity.py`
- `app/prompts/exam_support.py`
- `app/rag/build_index.py`
- `app/rag/chunker.py`
- `app/rag/embedder.py`
- `app/rag/rag_service.py`
- `app/rag/vector_store/bm25.pkl`
- `app/rag/vector_store/bm25_corpus.json`
- `app/rag/vector_store/index.faiss`
- `app/rag/vector_store/metadata.json`
- `app/schemas/chat_session.py`
- `app/schemas/feedback.py`
- `app/services/auth_service.py`
- `app/services/email_service.py`
- `app/services/llm_service.py`
- `app/services/logging_service.py`
- `app/services/report_service.py`
- `app/services/stt_service.py`
- `app/services/topic_service.py`
- `app/services/tts_service.py`

## Backend — file mới bổ sung (18)

- `.gitignore`
- `.python-version`
- `app/rag/evidence_selector.py`
- `app/services/answer_postprocessor.py`
- `app/services/model_clients.py`
- `app/services/voice_correction_service.py`
- `DEPLOYMENT_GUIDE.md`
- `migrations/001_admin_retention_vn_timezone.sql`
- `migrations/002_trash_batches.sql`
- `migrations/003_case_insensitive_user_identity.sql`
- `pyproject.toml`
- `README.md`
- `requirements.txt`
- `tests/test_answer_postprocessor.py`
- `tests/test_auth_identity.py`
- `tests/test_evidence_selector.py`
- `tests/test_rag_pipeline.py`
- `uv.lock`

## Backend — file bị xoá (11)

- `app/api/v1/admin_v6.py`
- `app/api/v1/auth_v6.py`
- `app/api/v1/chat_v6.py`
- `app/db/test_connection.py`
- `app/models/chat_log_v6.py`
- `app/rag/data/Huong dan danh cho giam thi coi thi EOS_31.12.25.original_before_dedup.bak`
- `app/rag/loader.py`
- `app/services/email_service_v1.py`
- `app/services/rag_service.py`
- `sql/20260613_add_report_indexes.sql`
- `sql/20260613_create_rag_documents.sql`

## Frontend — file đã thay đổi (56)

- `.env.example`
- `components.json`
- `eslint.config.js`
- `index.html`
- `package.json`
- `package-lock.json`
- `postcss.config.js`
- `public/robots.txt`
- `src/App.tsx`
- `src/components/admin/AdminLayout.tsx`
- `src/components/admin/AdminProtectedRoute.tsx`
- `src/components/chat/AudioVisualizer.tsx`
- `src/components/chat/ChatInput.tsx`
- `src/components/chat/ChatMessage.tsx`
- `src/components/chat/ChatWindow.tsx`
- `src/components/chat/QuickActions.tsx`
- `src/components/chat/TypingIndicator.tsx`
- `src/components/chat/VoiceModeOverlay.tsx`
- `src/components/Header.tsx`
- `src/components/ProtectedRoute.tsx`
- `src/components/ui/alert.tsx`
- `src/components/ui/button.tsx`
- `src/components/ui/card.tsx`
- `src/components/ui/input.tsx`
- `src/components/ui/label.tsx`
- `src/components/ui/progress.tsx`
- `src/components/ui/select.tsx`
- `src/components/ui/sonner.tsx`
- `src/components/ui/textarea.tsx`
- `src/components/ui/tooltip.tsx`
- `src/context/AuthContext.tsx`
- `src/index.css`
- `src/lib/utils.ts`
- `src/main.tsx`
- `src/pages/About.tsx`
- `src/pages/admin/AdminDashboard.tsx`
- `src/pages/admin/AdminSettings.tsx`
- `src/pages/admin/ChatbotData.tsx`
- `src/pages/admin/FeedbackManagement.tsx`
- `src/pages/admin/Reports.tsx`
- `src/pages/admin/UsersManagement.tsx`
- `src/pages/ForgotPassword.tsx`
- `src/pages/Index.tsx`
- `src/pages/Login.tsx`
- `src/pages/NotFound.tsx`
- `src/pages/Register.tsx`
- `src/pages/ResetPassword.tsx`
- `src/pages/VerifyEmail.tsx`
- `src/test/setup.ts`
- `src/vite-env.d.ts`
- `tailwind.config.ts`
- `tsconfig.app.json`
- `tsconfig.json`
- `tsconfig.node.json`
- `vite.config.ts`
- `vitest.config.ts`

## Frontend — file mới bổ sung (9)

- `.env`
- `.gitattributes`
- `.gitignore`
- `DEPLOYMENT_GUIDE.md`
- `README.md`
- `src/assets/Logo-Dai-hoc-FPT.webp`
- `src/context/auth.ts`
- `src/lib/api-errors.ts`
- `src/test/api.test.ts`

## Frontend — file bị xoá (54)

- `.env.development`
- `.env.production`
- `bun.lockb`
- `public/placeholder.svg`
- `requirements.txt`
- `src/App.css`
- `src/assets/Logo-Dai-hoc-FPT.jpg`
- `src/components/admin/UsersTable.tsx`
- `src/components/auth/AuthLayout.tsx`
- `src/components/chat/ChatMessage_v1.tsx`
- `src/components/NavLink.tsx`
- `src/components/ui/accordion.tsx`
- `src/components/ui/alert-dialog.tsx`
- `src/components/ui/aspect-ratio.tsx`
- `src/components/ui/avatar.tsx`
- `src/components/ui/badge.tsx`
- `src/components/ui/breadcrumb.tsx`
- `src/components/ui/calendar.tsx`
- `src/components/ui/carousel.tsx`
- `src/components/ui/chart.tsx`
- `src/components/ui/checkbox.tsx`
- `src/components/ui/collapsible.tsx`
- `src/components/ui/command.tsx`
- `src/components/ui/context-menu.tsx`
- `src/components/ui/dialog.tsx`
- `src/components/ui/drawer.tsx`
- `src/components/ui/dropdown-menu.tsx`
- `src/components/ui/form.tsx`
- `src/components/ui/hover-card.tsx`
- `src/components/ui/input-otp.tsx`
- `src/components/ui/menubar.tsx`
- `src/components/ui/navigation-menu.tsx`
- `src/components/ui/pagination.tsx`
- `src/components/ui/popover.tsx`
- `src/components/ui/radio-group.tsx`
- `src/components/ui/resizable.tsx`
- `src/components/ui/scroll-area.tsx`
- `src/components/ui/separator.tsx`
- `src/components/ui/sheet.tsx`
- `src/components/ui/sidebar.tsx`
- `src/components/ui/skeleton.tsx`
- `src/components/ui/slider.tsx`
- `src/components/ui/switch.tsx`
- `src/components/ui/table.tsx`
- `src/components/ui/tabs.tsx`
- `src/components/ui/toast.tsx`
- `src/components/ui/toaster.tsx`
- `src/components/ui/toggle.tsx`
- `src/components/ui/toggle-group.tsx`
- `src/components/ui/use-toast.ts`
- `src/hooks/use-mobile.tsx`
- `src/hooks/use-toast.ts`
- `src/lib/mockResponses.ts`
- `src/test/example.test.ts`
