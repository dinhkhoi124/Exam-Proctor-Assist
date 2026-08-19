# Laptop update: localhost app + API models

This laptop intentionally differs from the Ubuntu PC: it runs FastAPI, React, embeddings, PDF/OCR and RAG locally, while LLM, Vision and STT are called through an OpenAI-compatible API.

## Implemented changes

- Limits concurrent model calls (`LLM_MAX_CONCURRENCY`) and blocking RAG work (`RAG_MAX_CONCURRENCY`) so API latency does not block FastAPI's event loop.
- Converts uploaded images to correctly oriented, bounded JPEGs before the Vision API call. The original image is not sent again in the answer request, reducing cost and preserving context for RAG evidence.
- Adds one-active-login session invalidation. A newer login invalidates earlier JWTs and the frontend explains why it redirected to login.
- Restores batch RAG document management: managers can upload or replace up to 20 PDFs in one operation, or select and delete up to 100 documents. The index rebuilds once per batch and the complete batch is rolled back if rebuilding fails.
- Adds migration `004_single_active_session.sql`.
- Adds Windows CPU/API and CUDA-embedding/API dependency files, plus an API-model environment template.

## Apply configuration

1. Copy `backend/.env.api.example` to `backend/.env` or merge its variables into the laptop's existing `.env`.
2. Set `OPENAI_API_KEY`, `DATABASE_URL`, `JWT_SECRET` and `EMAIL_ENCRYPT_KEY`. Do not copy the Ubuntu PC `.env`.
3. Keep `LLM_BASE_URL`, `VISION_BASE_URL` and `STT_BASE_URL` blank for OpenAI. For another OpenAI-compatible provider, set the provider's `/v1` endpoint and corresponding API keys.
4. Keep `frontend/.env.development` at `VITE_API_URL=http://127.0.0.1:8000`.

## Database migration

Back up the laptop database, then run migration 004 once against that database before starting the new backend:

```powershell
psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f backend\migrations\004_single_active_session.sql
```

Existing tokens will require users to sign in again; this is expected.

## Batch PDF management

The **Quản lý tài liệu** page supports selecting multiple PDFs at once.

- Maximum 20 PDFs per upload batch.
- Maximum 25 MB for each PDF and 90 MB for a complete upload batch.
- Existing filenames require confirmation before replacement; duplicate names are rejected case-insensitively.
- Select rows (or select all filtered rows) to delete up to 100 documents in one operation.
- Upload, replacement, and deletion each rebuild the RAG index once. If rebuilding or metadata synchronization fails, all file, metadata and FAISS/BM25 index changes are restored.

## Install and run on Windows

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
# Choose one profile. CPU:
.\.venv\Scripts\python.exe -m pip install -r requirements-windows-api.txt
# Or NVIDIA GPU embeddings while still using API models for LLM/Vision/STT:
# .\.venv\Scripts\python.exe -m pip install -r requirements-windows-api-cuda.txt
.\.venv\Scripts\python.exe -m app.rag.build_index
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Do not run the Ubuntu vLLM/PhoWhisper/Faster-Whisper launch scripts or copy local-model weights on an API-only Windows host. Rebuild the RAG index only when that host's PDFs/parser/chunking/embedding settings change.

For the CPU profile set `EMBEDDING_DEVICE=cpu`. For the CUDA profile set
`EMBEDDING_DEVICE=cuda`, then verify before startup:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Image-only/scanned PDFs have no text layer. Set `RAG_OCR_SCAN_EMPTY_PAGES=true`
only when those documents must be indexed, then rebuild the index; OCR will make
the rebuild substantially slower. With the default `false`, a new PDF that
produces no usable chunks is rejected and rolled back instead of silently
installing an empty document.
