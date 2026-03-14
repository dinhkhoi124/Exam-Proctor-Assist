# 🔴 PHẢI Ở DÒNG ĐẦU TIÊN
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.api.v1.speech import router as speech_router
from app.api.v1.auth import router as auth_router
from app.models import user


app = FastAPI(
    title="RAG Chatbot Backend",
    version="1.0"
)

# CORS – cho frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Backend is running"}

app.include_router(chat_router, prefix="/api/v1")
app.include_router(speech_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
