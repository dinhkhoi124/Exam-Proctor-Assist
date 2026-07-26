import asyncio
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.stt_service import speech_to_text
from app.services.voice_correction_service import VoiceCorrectionService
from app.core.config import VOICE_CORRECTION_ENABLED


router = APIRouter()
logger = logging.getLogger(__name__)

# Khởi tạo voice correction service
voice_service = VoiceCorrectionService()


@router.post("/speech/stt")
async def stt(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    if not audio_bytes:
        return {"text": ""}

    # =========================
    # STEP 1: Speech to Text
    # =========================
    try:
        raw_text = await asyncio.to_thread(
            speech_to_text, audio_bytes, file.filename or "recording.webm"
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail="Dịch vụ nhận dạng giọng nói gặp lỗi.",
        ) from exc

    logger.info("Speech transcript received (characters=%d)", len(raw_text))

    if not raw_text:
        return {"text": ""}

    # =========================
    # STEP 2: Voice Correction
    # =========================
    corrected_text = (
        await voice_service.fix_voice_query(raw_text)
        if VOICE_CORRECTION_ENABLED
        else raw_text
    )

    logger.info(
        "Speech transcript normalization completed (characters=%d)",
        len(corrected_text),
    )

    return {
        "text": corrected_text,
        "raw_text": raw_text,
        "corrected": VOICE_CORRECTION_ENABLED,
    }
