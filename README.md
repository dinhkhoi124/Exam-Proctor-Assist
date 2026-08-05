# FPT Exam Assistant

AI-powered chatbot designed to support **exam proctors and students** in quickly accessing **exam regulations and academic policies**.

The system combines **Hybrid Retrieval-Augmented Generation (RAG)** with a **domain fine-tuned language model** to deliver accurate, context-grounded answers from official university documents — with both text and voice interaction.

> **Demo:** `https://drive.google.com/file/d/1zOehgN_HM-6vAPCKc0fsHZJW_Eh9R4cd/view?usp=sharing`

---

## Related Repositories

| Repository | Description |
|---|---|
| 🔬 [Exam-Assist-Benchmark](https://github.com/dmt171004/Exam-Assist-Benchmark) | Benchmarking framework — automatic metrics, LLM-as-a-Judge, efficiency analysis |
| 🧪 [Exam-Assist-Finetuning](https://github.com/dmt171004/Exam-Assist-Finetuning) | Fine-tuning pipeline for Qwen3-VL on exam-support domain data |

---

## Overview

**FPT Exam Assistant** allows exam proctors and students to ask questions via text or voice and instantly receive answers grounded in official university PDF documents.

Core capabilities:
- Exam regulation Q&A (text and voice)
- Academic policy lookup with source citation
- Step-by-step guidance with inline images from source PDFs
- Full authentication and user management
- Admin dashboard with analytics, feedback, RAG document management, and reporting

---

## Key Features

### Hybrid RAG Pipeline

The retrieval pipeline combines BM25 sparse search and multilingual-E5-base dense search, merged via Weighted Reciprocal Rank Fusion:

```
User Question / Voice Transcript
        │
        ▼
  Query Normalization (rule-based)
        │
        ├─── BM25 top-30 (rank-bm25)
        │
        └─── Dense top-30 (multilingual-E5-base, CPU)
                │
                ▼
        Weighted RRF (k=60, 0.5 / 0.5)
                │
                ▼
  Exact / Heading / Intent Boost
                │
                ▼
  Child → Parent Chunk Aggregation
                │
                ▼
  Deduplication + Confidence Gate
  (RAG_MIN_DENSE_SCORE / RAG_MIN_BM25_SCORE)
                │
                ▼
  ≤ 5 Evidence Parent Chunks
                │
                ▼
  LLM Answer + Evidence ID Citation (E1, E2, …)
                │
                ▼
  Illustrative Images (from best-scoring source PDF)
```

### Language Model Support

The system is model-agnostic. Two configurations are supported out of the box:

| Mode | LLM | STT |
|---|---|---|
| **Local (default)** | `qwen3-exam-assist` via vLLM (OpenAI-compatible API) | `faster-whisper-medium` via CTranslate2 CPU service |
| **OpenAI fallback** | `gpt-4o-mini` | `gpt-4o-mini-transcribe` / `whisper-1` |

Switching between modes requires only `.env` changes — no code modifications needed.

### Voice Interaction

- Speech-to-Text: local **Faster-Whisper** (CTranslate2, CPU `int8`) with WebRTC VAD pre-filter, served as an OpenAI-compatible API at `http://127.0.0.1:8002/v1`
- Deterministic voice correction applied before query submission
- Fallback to OpenAI STT configurable via environment variables

### Authentication & User Management

- JWT-based registration, login, email verification, password reset
- Soft delete with 30-day retention, trash/restore/permanent delete UI
- Case-insensitive email and username identity
- Admin management: batch delete chat sessions, purge expired accounts (background advisory-lock task)

### Admin Dashboard

| Module | Description |
|---|---|
| **Dashboard** | Usage statistics, active users, session counts |
| **Users Management** | Full CRUD, soft delete, trash batches, restore |
| **Chatbot Data** | RAG document upload, activation, deletion |
| **Feedback Management** | View and filter user feedback logs |
| **Reports** | Generated analytics reports with chart export |
| **Settings** | Email SMTP configuration |

---

## Tech Stack

### Backend

| Layer | Technology |
|---|---|
| Framework | **FastAPI** (Python 3.12) |
| ORM / DB | **SQLAlchemy** + **PostgreSQL** |
| Auth | **JWT** (`python-jose`) + **bcrypt** |
| RAG – Dense | `intfloat/multilingual-E5-base` (sentence-transformers, CPU) |
| RAG – Sparse | **BM25** (`rank-bm25`) |
| RAG – Index | **FAISS** (`faiss-cpu`) |
| PDF Parsing | `pdfplumber`, `pymupdf`, `pdfminer-six` |
| LLM Client | OpenAI-compatible (`openai` SDK) → local vLLM or OpenAI API |
| STT | **Faster-Whisper** (CTranslate2) — local service; OpenAI fallback |
| Vietnamese NLP | `underthesea`, `rapidfuzz` |
| Packaging | `uv` + `pyproject.toml` |
| Real-time | WebSocket (`websockets`) |

### Frontend

| Layer | Technology |
|---|---|
| Framework | **React 18** + **TypeScript** |
| Build tool | **Vite** |
| Styling | **TailwindCSS** + Radix UI primitives |
| HTTP | **Axios** + **TanStack React Query** |
| Charts | **Recharts** |
| Auth state | Context API (`AuthContext`, `auth.ts`) |
| Testing | **Vitest** + Testing Library |

---

## System Architecture

```
            ┌──────────────────────┐
            │      Frontend        │
            │  React + Vite + TS   │
            └──────────┬───────────┘
                       │ REST API + WebSocket
                       ▼
            ┌──────────────────────┐
            │   FastAPI Backend    │
            └──────────┬───────────┘
                       │
      ┌────────────────┼─────────────────┐
      ▼                ▼                 ▼
 Auth Module      RAG Module        Speech Module
(JWT + PostgreSQL) (Hybrid BM25     (Faster-Whisper
                   + E5 + FAISS     CTranslate2 CPU
                   + LLM Answer)    or OpenAI STT)
                       │
                       ▼
              LLM Inference Server
         (local vLLM / OpenAI-compatible)
              qwen3-exam-assist
                  or GPT-4o-mini
```

---

## Project Structure

```
FPT-Assistant-v3/
│
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py           # Registration, login, password reset
│   │   │   ├── chat.py           # Chat Q&A endpoint
│   │   │   ├── chat_session.py   # Session management
│   │   │   ├── speech.py         # STT / TTS
│   │   │   ├── admin.py          # Admin operations, purge tasks
│   │   │   ├── feedback.py       # Feedback logging
│   │   │   ├── rag_documents.py  # RAG document CRUD
│   │   │   ├── reports.py        # Analytics reports
│   │   │   └── email_setting.py  # SMTP configuration
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── websocket.py
│   │   │
│   │   ├── db/
│   │   │   └── session.py
│   │   │
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── chat_log.py
│   │   │   ├── chat_session.py
│   │   │   ├── chat_topic.py
│   │   │   ├── feedback_log.py
│   │   │   ├── rag_document.py
│   │   │   ├── email_setting.py
│   │   │   └── user_activity.py
│   │   │
│   │   ├── prompts/              # LLM prompt templates
│   │   │
│   │   ├── rag/
│   │   │   ├── rag_service.py    # Main RAG orchestration
│   │   │   ├── retriever.py      # Hybrid BM25 + dense retrieval
│   │   │   ├── evidence_selector.py
│   │   │   ├── embedder.py
│   │   │   ├── chunker.py
│   │   │   ├── build_index.py
│   │   │   ├── data/             # Source PDF documents
│   │   │   └── vector_store/     # FAISS index, BM25, metadata
│   │   │
│   │   ├── schemas/              # Pydantic request/response models
│   │   │
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   ├── model_clients.py  # Unified LLM/vision client factory
│   │   │   ├── stt_service.py
│   │   │   ├── tts_service.py
│   │   │   ├── voice_correction_service.py
│   │   │   ├── answer_postprocessor.py
│   │   │   ├── auth_service.py
│   │   │   ├── email_service.py
│   │   │   ├── report_service.py
│   │   │   └── topic_service.py
│   │   │
│   │   └── main.py               # FastAPI app, routers, purge scheduler
│   │
│   ├── migrations/               # SQL migration scripts (001 → 002 → 003)
│   ├── tests/                    # pytest test suite
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── requirements-windows.txt
│   └── .env.example
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── chat/             # ChatInput, ChatMessage, VoiceModeOverlay, …
│       │   ├── admin/            # AdminLayout, AdminProtectedRoute
│       │   └── ui/               # Radix-based design system components
│       │
│       ├── context/
│       │   ├── AuthContext.tsx
│       │   └── auth.ts           # Auth contract / token helpers
│       │
│       ├── lib/
│       │   ├── api.ts
│       │   └── api-errors.ts
│       │
│       ├── pages/
│       │   ├── Login.tsx / Register.tsx / ForgotPassword.tsx
│       │   ├── ResetPassword.tsx / VerifyEmail.tsx
│       │   └── admin/
│       │       ├── AdminDashboard.tsx
│       │       ├── UsersManagement.tsx
│       │       ├── ChatbotData.tsx
│       │       ├── FeedbackManagement.tsx
│       │       ├── Reports.tsx
│       │       └── AdminSettings.tsx
│       │
│       └── test/
├── VERSION_COMPARISON_REPORT.md  # v2 → v3 diff report
└── README.md
```

---

## Installation Guide

### Prerequisites

- Python **3.12** + [`uv`](https://github.com/astral-sh/uv)
- Node.js **≥ 18** + npm
- PostgreSQL

---

### 1. Clone Repository

```bash
git clone https://github.com/dinhkhoi124/FPT-Assistant-v3.git
cd FPT-Assistant-v3
```

---

### 2. Backend Setup

```bash
cd backend
cp .env.example .env
uv sync
```

Edit `.env` and fill in your database URL, JWT secret, and model configuration (see section below).

---

### 3. Configure Environment Variables

Key variables in `backend/.env`:

```dotenv
# ── LLM (local vLLM — default) ──────────────────────────────
LLM_BASE_URL=http://127.0.0.1:8001/v1
LLM_API_KEY=local
LLM_MODEL=qwen3-exam-assist

# ── LLM (switch to OpenAI — clear BASE_URL) ─────────────────
# LLM_BASE_URL=
# LLM_API_KEY=sk-...
# LLM_MODEL=gpt-4o-mini

# ── STT (local Faster-Whisper) ───────────────────────────────
STT_BASE_URL=http://127.0.0.1:8002/v1
STT_API_KEY=local
STT_MODEL=faster-whisper-medium

# ── STT (switch to OpenAI STT — clear BASE_URL) ─────────────
# STT_BASE_URL=
# OPENAI_API_KEY=sk-...

# ── Database ─────────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/fpt_exam_support

# ── Auth ─────────────────────────────────────────────────────
JWT_SECRET=your-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── Frontend CORS ─────────────────────────────────────────────
FRONTEND_URL=http://localhost:8080
FRONTEND_ORIGINS=http://localhost:8080

# ── RAG thresholds ───────────────────────────────────────────
RAG_MIN_DENSE_SCORE=0.83
RAG_MIN_BM25_SCORE=20.0
```

---

### 4. Run Database Migrations

Apply the three backend migrations in order:

```bash
psql -d fpt_exam_support -f backend/migrations/001_admin_retention_vn_timezone.sql
psql -d fpt_exam_support -f backend/migrations/002_trash_batches.sql
psql -d fpt_exam_support -f backend/migrations/003_case_insensitive_user_identity.sql
```

---

### 5. (Optional) Start Local LLM Server

From the `Chatbot_Module` directory, run the fine-tuned Qwen3 model via vLLM:

```bash
./scripts/run_qwen_vllm.sh
```

Served at `http://127.0.0.1:8001/v1` as model `qwen3-exam-assist`.

---

### 6. (Optional) Start Local STT Server

```bash
./scripts/run_faster_whisper_cpu.sh
```

Served at `http://127.0.0.1:8002/v1`. Uses WebRTC VAD to skip silent audio. Model lazy-loads on the first voiced request.

---

### 7. Run Backend Server

```bash
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

---

### 8. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at: `http://localhost:5173`

---

### 9. Rebuild RAG Index (when source documents change)

```bash
cd backend
uv run python -m app.rag.build_index
```

> **Note:** `index.faiss`, `bm25.pkl`, `bm25_corpus.json`, and `metadata.json` must always be kept in sync with each other and with the source PDFs in `app/rag/data/`.

---

## Related Repositories

### 🔬 Benchmark Repository

Evaluates pretrained vs. fine-tuned models using automatic metrics (Exact Match, F1, ROUGE-L, Containment Accuracy) and LLM-as-a-Judge (Correct Refusal Rate, Hallucination Rate, Faithfulness).

➡️ [https://github.com/dmt171004/Exam-Assist-Benchmark](https://github.com/dmt171004/Exam-Assist-Benchmark)

### 🧪 Fine-tuning Repository

Contains the QLoRA training pipeline (`scripts/`), dataset preparation (`data/`), and fine-tuning outputs (`outputs/`) for adapting Qwen3-VL to the exam-support domain.

➡️ [https://github.com/dmt171004/Exam-Assist-Finetuning](https://github.com/dmt171004/Exam-Assist-Finetuning)

---

## Authors

**Dinh Van Anh Khoi · Duong Minh Tri · Tran Song Toan · Truong Loi Vi**

---

## License

This project is developed for **educational and research purposes**.
