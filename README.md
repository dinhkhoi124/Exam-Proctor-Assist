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

# Future Improvements

Potential improvements for production deployment:

- Deploy App
- Document upload interface for administrators
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
