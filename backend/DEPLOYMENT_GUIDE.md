# FPT Exam Support - Tong hop nang cap va huong dan deploy

Tai lieu nay mo ta ban cap nhat cua `Chatbot_Module`, tap trung vao thay doi PostgreSQL va cach dua backend/frontend sang may moi.

## 1. Cac nang cap da thuc hien

### Quan ly nhat ky hoat dong

- Bo sung bo loc theo **tuan**, ben canh ngay/thang/nam.
- Tat ca moc thoi gian loc, hien thi va xuat bao cao duoc quy ve `Asia/Ho_Chi_Minh`.
- Cho phep chon nhieu ban ghi de xoa mem.
- Cho phep xoa theo tai khoan va khoang ngay/tuan/thang/nam.
- Chi tiet mot chat session hien thi day du moi luot hoi/dap, khong con chi hien thi ban ghi dau tien.
- Danh dau nguon xoa session: nguoi dung tu xoa (`self_service`), admin xoa (`admin`) hoac du lieu cu khong xac dinh (`unknown`).

### Thung rac va vong doi du lieu

- Chat session/chat log bi xoa duoc xoa mem va gom theo `deletion_batch_id`.
- Admin co the xem, khoi phuc hoac xoa vinh vien tung nhom trong thung rac.
- Tai khoan bi xoa mem co the khoi phuc trong 30 ngay.
- Sau 30 ngay, scheduler an danh hoa thong tin ca nhan; ban ghi user duoc giu lai de bao toan khoa ngoai va lich su audit.
- Xoa vinh vien tu thung rac cung dung co che an danh hoa an toan.

### Quan ly nguoi dung va phan quyen

- Admin co the khoa/mo khoa tai khoan.
- Admin co the xoa mem, khoi phuc va xoa vinh vien/an danh hoa tai khoan.
- Chan admin tu xoa/khoa chinh minh va bao ve cac role khong duoc phep thao tac.
- Kiem tra quyen so huu chat session va feedback, ngan truy cap cheo tai khoan.
- Email va username dang nhap khong con phan biet chu hoa/chu thuong.
- Email duoc trim va luu chu thuong khi dang ky; username duoc trim.
- Dang ky dong thoi bi unique index chan va tra HTTP 409 thay vi 500.

### Dashboard, bao cao va giao dien

- Sua truy van dashboard/join/filter gay loi tai du lieu bang dieu khien.
- Xuat XLSX/PDF theo ngay/tuan/thang/nam voi timezone Viet Nam.
- Sua export XLSX voi datetime co timezone.
- Header `FPT Exam Support` bam le trai; responsive khong tran ngang tu 320px.
- Sidebar chat chuyen thanh drawer tren mobile; input co safe-area cho iPhone.
- Lazy-load cac route: bundle chinh giam tu khoang 961 KB xuong 354 KB.
- Chuan hoa line ending LF va them `.gitattributes`.

### RAG/Chat/Feedback

- Bao toan thuat ngu nghiep vu trong query rewrite.
- Bo sung confidence gate, evidence selection va post-processing cho cau tra loi.
- Feedback chi duoc tao cho chat thuoc dung tai khoan.
- Cac chat da xoa khong con xuat hien o phia nguoi dung nhung van duoc admin quan ly trong thung rac.

## 2. Thay doi database PostgreSQL

Cac migration nam trong `backend/migrations/` va phai chay dung thu tu.

### Migration 001 - `001_admin_retention_vn_timezone.sql`

- Tao bang `schema_migrations`.
- Them vao `users`: `is_deleted`, `deleted_at`, `deleted_by`, `delete_reason`, `purged_at`, `locked_at`, `locked_by`.
- Them vao `chat_logs`: `is_deleted`, `deleted_at`, `deleted_by`.
- Chuyen cac cot thoi gian chinh sang `TIMESTAMPTZ`, coi du lieu timestamp cu la gio `Asia/Ho_Chi_Minh`.
- Dat lai khoa ngoai quan trong:
  - `chat_logs.user_id -> users.id`: `ON DELETE RESTRICT`.
  - `chat_sessions.user_id -> users.id`: `ON DELETE RESTRICT`.
  - `user_activity_logs.user_id -> users.id`: `ON DELETE RESTRICT`.
  - `user_sessions.user_id -> users.id`: `ON DELETE RESTRICT`.
  - Cac cot actor nhu `deleted_by`, `locked_by`: `ON DELETE SET NULL`.
- Tao index cho user/chat dang hoat dong va du lieu da xoa.

### Migration 002 - `002_trash_batches.sql`

- Them `deleted_at`, `deleted_by`, `deletion_batch_id` vao `chat_sessions`.
- Them `deletion_batch_id` vao `chat_logs`.
- Backfill metadata cho session/log da bi xoa tu truoc.
- Dong bo log con khi session cha da bi xoa.
- Tao index partial cho batch thung rac va thoi diem xoa.

### Migration 003 - `003_case_insensitive_user_identity.sql`

- Kiem tra va dung migration neu con email/username trung khi so sanh khong phan biet hoa-thuong.
- Chuan hoa email bang `lower(trim(email))`, trim username.
- Tao unique index:
  - `uq_users_email_case_insensitive` tren `lower(email)`.
  - `uq_users_username_case_insensitive` tren `lower(username)`.

DBTest hien da ap dung du `001`, `002`, `003`, timezone mac dinh la `Asia/Ho_Chi_Minh`, khong con orphan va khong con nhom email/username trung. Hai tai khoan trung khong co tham chieu da duoc khoa va an danh hoa; tai khoan co lich su duoc giu lai.

## 3. Chay migration tren may moi

Luon backup database truoc. Tu thu muc `backend`:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/001_admin_retention_vn_timezone.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/002_trash_batches.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/003_case_insensitive_user_identity.sql
```

Truoc migration 003, kiem tra duplicate:

```sql
SELECT lower(trim(email)), count(*) FROM users GROUP BY lower(trim(email)) HAVING count(*) > 1;
SELECT lower(trim(username)), count(*) FROM users GROUP BY lower(trim(username)) HAVING count(*) > 1;
```

Neu co ket qua, phai chon tai khoan can giu va hoa giai du lieu truoc; migration 003 co chu y rollback thay vi tu dong xoa tai khoan.

Dat timezone database (thay ten database neu can):

```sql
ALTER DATABASE "DBTest" SET timezone TO 'Asia/Ho_Chi_Minh';
```

Backend cung tu dat timezone cho moi connection, nen van dung neu PostgreSQL server co timezone mac dinh khac.

## 4. Cau hinh OpenAI GPT-4o mini

Goi backend co file `.env` da tao tu cau hinh hien tai voi:

```dotenv
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
QUERY_REWRITE_MODEL=gpt-4o-mini
VISION_BASE_URL=
VISION_API_KEY=
VISION_MODEL=gpt-4o-mini
LLM_REPETITION_PENALTY=1.0
STT_BASE_URL=
STT_API_KEY=
STT_MODEL=gpt-4o-mini-transcribe
STT_FALLBACK_MODEL=whisper-1
```

`OPENAI_API_KEY` duoc dung chung khi cac key rieng de trong. OCR o day la vision extraction bang `gpt-4o-mini`. ASR phai dung model endpoint transcription `gpt-4o-mini-transcribe`, khong dung truc tiep `gpt-4o-mini`.

Sau khi copy sang may moi, kiem tra lai it nhat: `DATABASE_URL`, `JWT_SECRET`, `OPENAI_API_KEY`, mail credentials, `FRONTEND_URL`, `FRONTEND_ORIGINS` va cac domain deploy.

## 5. Deploy backend

Yeu cau khuyen nghi: Python 3.12, PostgreSQL va `uv`.

```bash
cd backend
uv sync --frozen
# Hoac dung pip:
python -m pip install -r requirements.txt
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`requirements.txt` la ban export day du tu `uv.lock`, bao gom dependency truc tiep va bac cau cua RAG, PyTorch/CUDA va faster-whisper. Neu may deploy CPU-only, nen dung `uv sync --frozen` theo lock/project va can nhac tao lock CPU rieng de tranh tai cac goi CUDA lon.

Thu muc `app/rag/data` va `app/rag/vector_store` da nam trong goi backend, nen co the truy van ngay ma khong can build lai index. Neu thay tai lieu, chay:

```bash
uv run python -m app.rag.build_index
```

## 6. Deploy frontend

```bash
cd frontend
npm ci
npm run build
```

Deploy noi dung `dist/` bang Nginx/static hosting, hoac chay kiem tra:

```bash
npm run preview -- --host 0.0.0.0
```

Kiem tra bien API endpoint cua frontend truoc build neu domain backend tren may moi khac cau hinh hien tai.

## 7. Kiem tra sau deploy

- Dang nhap bang email/username voi chu hoa-thuong khac nhau.
- Dashboard admin tai duoc thong ke.
- Loc nhat ky theo tuan va xem du cac luot chat trong session.
- Xoa session o user, xac nhan admin thay nhan `self_service` trong thung rac.
- Thu khoa/mo khoa, xoa mem va khoi phuc mot tai khoan test.
- Xuat XLSX/PDF va kiem tra moc gio Viet Nam.
- Thu OCR anh va ASR am thanh voi OpenAI key cua moi truong deploy.

## 8. Luu y bao mat

Archive backend deploy co chua `.env` va do do co the chua credential. Chi truyen qua kenh an toan, khong commit archive hoac `.env` len Git, va nen rotate key neu archive bi chia se sai nguoi.
