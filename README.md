# FPT Exam Assistant

AI-powered chatbot designed to support **exam proctors and students** in quickly accessing **exam regulations and academic policies**.  

The system leverages **Retrieval-Augmented Generation (RAG)** to provide accurate answers from official university documents, combined with **speech capabilities** for voice interaction.

This project demonstrates how modern AI systems integrate **LLMs, vector search, and web applications** to build intelligent assistants for educational environments.

---

# Introduction

DEMO LINK: ``` https://drive.google.com/drive/folders/1qb7H7sxLXqCxdXK33WfDRCM7p0oMOvCr?usp=sharing ```

**FPT Exam Assistant** is an AI chatbot designed to assist **exam proctors and students** by providing instant access to university exam regulations and academic policies.

Instead of manually searching through lengthy PDF documents, users can simply **ask questions via text or voice**, and the chatbot will retrieve relevant information from official documents using **Retrieval-Augmented Generation (RAG)**.

The system supports:

- Exam regulation Q&A
- Academic policy lookup
- Voice-based interaction
- Secure authentication
- Retrieval from official documents

This project serves as a **prototype for an AI-powered university exam support system**.

---

# Key Features

## AI Question Answering

Users can ask questions related to:

- exam regulations
- academic rules
- exam procedures
- student policies

The chatbot retrieves relevant document chunks and generates answers using **GPT-4o**.

---

## Retrieval-Augmented Generation (RAG)

The system improves answer reliability by retrieving information directly from **official PDF documents**.

### RAG Pipeline

```
User Question
│
▼
Embedding (OpenAI)
│
▼
Vector Search (FAISS)
│
▼
Relevant Document Chunks
│
▼
Prompt + Context
│
▼
GPT-4o Answer

```
---

## Voice Interaction

Users can interact with the system using voice.

Supported features:

- Speech-to-Text using **gpt-4o-mini-transcribe**
- Voice question input

---

## Authentication System

The system includes a full authentication flow:

- User registration
- Login with JWT
- Secure password handling
- Token expiration

---

## Step-by-Step Instructions with Images

The chatbot can also provide **step-by-step guidance with text and images**, helping users understand procedures such as:

- exam registration
- exam regulations
- administrative processes

---

# Tech Stack

## Backend

- **FastAPI**
- **Python**
- **SQLAlchemy**
- **PostgreSQL**
- **JWT Authentication**
- **FAISS (Vector Database)**

---

## AI / LLM

- **OpenAI GPT-4o**
- **OpenAI Embeddings**
- **gpt-4o-mini-transcribe** (Speech-to-Text)

---

## RAG System

- Document parsing
- Text chunking
- Embedding generation
- FAISS vector search
- Context injection into LLM prompts

---

## Frontend

- **React**
- **TypeScript**
- **Vite**
- **TailwindCSS**
- **Axios**

---

# System Architecture
```

            ┌───────────────────┐
            │     Frontend      │
            │  React + Vite UI  │
            └─────────┬─────────┘
                      │ REST API
                      ▼
            ┌───────────────────┐
            │      FastAPI      │
            │      Backend      │
            └─────────┬─────────┘
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼

Authentication RAG Module Speech API
(JWT + PostgreSQL) (FAISS + LLM) (Transcribe)

                      │
                      ▼
                OpenAI API
               (GPT-4o + Embedding)

```
---

# Project Structure

```

CHATBOT_EXAM_ASSISTANT_V2
│
├── backend
│ ├── app
│ │ ├── api/v1
│ │ │ ├── auth
│ │ │ ├── chat
│ │ │ └── speech
│ │ │
│ │ ├── core
│ │ │ └── config, logger
│ │ │
│ │ ├── db
│ │ │ └── database connection
│ │ │
│ │ ├── models
│ │ │ └── database models
│ │ │
│ │ ├── prompts
│ │ │ └── LLM prompt templates
│ │ │
│ │ ├── rag
│ │ │ └── retrieval pipeline
│ │ │
│ │ ├── schemas
│ │ │ └── request/response validation
│ │ │
│ │ ├── services
│ │ │ └── business logic
│ │ │
│ │ └── main.py
│ │
│ ├── static
│ ├── test
│ ├── requirements.txt
│ └── .env
│
├── frontend
│ ├── public
│ ├── src
│ │ ├── components
│ │ ├── context
│ │ ├── hooks
│ │ ├── lib
│ │ ├── pages
│ │ └── test
│ │
│ ├── package.json
│ ├── tailwind.config.ts
│ └── vite.config.ts
│
└── README.md

```

---

## Installation Guide

Follow these steps to run the project locally.

---

## 1 Clone Repository

```
git clone https://github.com/YOUR_GITHUB/FPT-Exam-Assistant.git

cd FPT-Exam-Assistant
```

---

## 2 Backend Setup

Navigate to backend directory:

```
cd backend
```

Create virtual environment:

```
python -m venv .venv
```

Activate environment:

### Windows

```
.venv\Scripts\activate
```

Install dependencies:

```
pip install -r requirements.txt
```

---

## 3 Configure Environment Variables

Create `.env` file inside backend folder.

Example:
```

OPENAI_API_KEY= enter-your-API-Keys

DATABASE_URL= enter-your-Keys

JWT_SECRET= enter-your-Keys
JWT_ALGORITHM= enter-your-Keys
ACCESS_TOKEN_EXPIRE_MINUTES= enter-your-Keys

RESET_TOKEN_EXPIRE_MINUTES= enter-your-Keys

MAIL_USERNAME= enter-your-Keys

MAIL_PASSWORD= enter-your-Keys
MAIL_FROM= enter-your-Keys

MAIL_PORT= enter-your-Keys
MAIL_SERVER= enter-your-Keys

MAIL_TLS=True
MAIL_SSL=False
```

---

## 4 Setup PostgreSQL

Create a PostgreSQL database and update:

```
DATABASE_URL= enter-your-Keys
```
---

## 5 Run Backend Server

```
uvicorn app.main:app --reload
```

Backend will run at:

```
http://localhost:8000
```

API docs available at:

```
http://localhost:8000/docs
```

---

## 6 Frontend Setup

Navigate to frontend directory:

```
cd frontend
```

Install dependencies:

```
npm install
```

Run development server:

```
npm run dev
```

Frontend will run at:

```
http://localhost:5173
```

---

# Recent Updates (2026-08-14)

## Admin dashboard and reports

- Dashboard question totals and charts now support four account scopes: `user`, `admin`, `manager`, and `all`.
- End-user traffic remains the default scope so admin/management test prompts do not inflate production usage statistics.
- The selected scope is shared between Dashboard and Reports through browser local storage.
- Report previews refresh immediately when the scope changes; a manual page refresh is no longer required.
- Excel and PDF exports apply the selected account scope, include it in the report metadata, and add it to the downloaded filename.
- The report layout is responsive: filters stack on phones, export buttons become full-width, summary cards adapt by breakpoint, and charts avoid horizontal overflow.

API query parameters:

```text
GET /api/v1/admin/stats?question_scope=user
GET /api/v1/admin/metrics?range=day&question_scope=user
GET /api/v1/admin/reports/preview?...&question_scope=user
GET /api/v1/admin/reports/export?...&question_scope=user&format=xlsx
```

## Document management

- Added client-side PDF filename search that is case-insensitive and Vietnamese accent-insensitive.
- Search results continue to support every existing sort option.
- Added a correctly aligned clear button, match counter, empty-result state, and responsive mobile controls.

## Chat citation images

- Replaced the browser `about:blank` image-opening flow with an in-app lightbox.
- Citation images can be enlarged without leaving the conversation.
- The lightbox supports Escape, backdrop close, keyboard focus, body-scroll locking, and touch-friendly responsive sizing.

## Verification

- Backend test suite: `pytest -q`
- Frontend static checks: `npm run lint`
- Frontend production bundle: `npm run build`

---

# Deployment profiles and API configuration

The backend supports two model-provider profiles without changing application
code:

- **API models on Windows/Linux:** FastAPI, PDF/OCR, embeddings and FAISS run on
  the host; LLM, Vision and STT use OpenAI or another OpenAI-compatible API.
- **Local models on Ubuntu:** LLM/Vision can point to a local vLLM endpoint and
  STT can point to the local PhoWhisper/Faster-Whisper service.

Never commit a real `.env`, API key, database password, `JWT_SECRET`,
`EMAIL_ENCRYPT_KEY`, internal PDF, FAISS index or model weight.

## Windows with API models

Use Python 3.12 and choose exactly one dependency profile:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

# CPU embeddings
.\.venv\Scripts\python.exe -m pip install -r requirements-windows-api.txt

# Or NVIDIA/CUDA 12.8 embeddings
# .\.venv\Scripts\python.exe -m pip install -r requirements-windows-api-cuda.txt
```

Copy `backend/.env.api.example` to `backend/.env`, then configure secrets and
provider values locally. Important API variables:

```dotenv
OPENAI_API_KEY=<secret>
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
VISION_BASE_URL=
VISION_API_KEY=
VISION_MODEL=gpt-4o-mini
STT_BASE_URL=
STT_API_KEY=
STT_MODEL=gpt-4o-mini-transcribe
STT_FALLBACK_MODEL=whisper-1
EMBEDDING_DEVICE=cpu
```

Leave a `*_BASE_URL` blank for OpenAI. For another OpenAI-compatible provider,
set its `/v1` endpoint, API key and published model name. Set
`EMBEDDING_DEVICE=cuda` only with the CUDA requirements file and a working
NVIDIA runtime.

For each server/domain, also change:

```dotenv
DATABASE_URL=<that server's database>
JWT_SECRET=<unique random secret>
EMAIL_ENCRYPT_KEY=<key matching that database's encrypted SMTP data>
FRONTEND_URL=https://<frontend-domain>
FRONTEND_ORIGINS=https://<frontend-domain>
```

Before building the frontend for each deployment, set:

```dotenv
VITE_API_URL=https://<public-backend-domain>
```

For `https://examsupport.visionlab.ai.vn/`, use that deployment's public backend
origin in `VITE_API_URL` and the frontend origin in `FRONTEND_URL` and
`FRONTEND_ORIGINS`. WebSocket `/ws/admin` must be proxied with upgrade headers.

## Database and document-management update

Run migration 004 once on every deployment database:

```powershell
psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f backend\migrations\004_single_active_session.sql
```

Document management supports:

- upload/replace up to 20 PDFs per batch;
- maximum 25 MB per PDF and 90 MB per upload batch;
- delete up to 100 selected PDFs per operation;
- rollback of PDF files, PostgreSQL metadata, FAISS/BM25 files and in-memory RAG
  resources if rebuilding fails;
- rejection of corrupt PDFs, documents producing no usable chunks, and Windows
  filename collisions that differ only by letter case.

Image-only PDFs require `RAG_OCR_SCAN_EMPTY_PAGES=true`; this makes indexing
slower. The complete API/local-model deployment matrix and operational notes are
in [API_DEPLOYMENT_NOTES.md](API_DEPLOYMENT_NOTES.md).

## Verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm test -- --run
npm run build
```

The regression tests were used locally before commit, but this update does not
add new files under `backend/tests`.

---

# Future Improvements

Potential improvements for production deployment:

- Deploy App
- Advanced RAG ranking
- Multi-language support
- Role-based access control
- Conversation memory with long-term context

---

# Authors

**Dinh Van Anh Khoi | Duong Minh Tri | Tran Song Toan | Truong Loi Vi** 

---

# License

This project is developed for **educational and research purposes**.
