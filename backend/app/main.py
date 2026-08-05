from dotenv import load_dotenv
import asyncio
import logging

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.api.v1.speech import router as speech_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import purge_expired_chat_trash, purge_expired_users, router as admin_router
from app.api.v1.email_setting import router as email_setting_router
from app.api.v1.chat_session import router as chat_session_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.rag_documents import router as rag_documents_router
from app.api.v1.reports import router as reports_router
from app.models import user
from fastapi import WebSocket, WebSocketDisconnect
from app.core.websocket import manager
from app.core.config import FRONTEND_ORIGINS
from app.db.session import SessionLocal
from sqlalchemy import text


logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Chatbot Backend",
    version="1.0"
)


_purge_task = None
_PURGE_LOCK_ID = 2026072430


async def _purge_deleted_users_loop():
    while True:
        db = SessionLocal()
        lock_acquired = False
        try:
            lock_acquired = bool(
                db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": _PURGE_LOCK_ID}).scalar()
            )
            if lock_acquired:
                purge_expired_users(db, retention_days=30)
                purge_expired_chat_trash(db, retention_days=30)
        except Exception:
            db.rollback()
            logger.exception("Scheduled retention purge failed")
            # The next daily run retries automatically; startup must remain available.
        finally:
            try:
                if lock_acquired:
                    db.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": _PURGE_LOCK_ID},
                    )
            except Exception:
                logger.exception("Failed to release the retention purge advisory lock")
            finally:
                db.close()
        await asyncio.sleep(24 * 60 * 60)


@app.on_event("startup")
async def start_user_purge_scheduler():
    global _purge_task
    _purge_task = asyncio.create_task(_purge_deleted_users_loop())


@app.on_event("shutdown")
async def stop_user_purge_scheduler():
    if _purge_task:
        _purge_task.cancel()
# CORS – cho frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(FRONTEND_ORIGINS + [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ])),
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
app.include_router(admin_router, prefix="/api/v1")
app.include_router(email_setting_router, prefix="/api/v1")
app.include_router(chat_session_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(rag_documents_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")

@app.websocket("/ws/admin")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
