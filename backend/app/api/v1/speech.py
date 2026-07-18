from fastapi import APIRouter, UploadFile, File
from app.services.stt_service import speech_to_text
from app.services.asr_correction_service import correct_asr_text
from app.core.config import VOICE_PIPELINE_MODE
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.services.tts_service import text_to_speech

router = APIRouter()

@router.post("/speech/stt")
async def stt(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    # 🔴 DEBUG BẮT BUỘC
    print("VOICE DEBUG")
    print("filename:", file.filename)
    print("bytes length:", len(audio_bytes))
    print("first 20 bytes:", audio_bytes[:20])

    if not audio_bytes or len(audio_bytes) < 8000:
        return {
            "text": "",
            "raw_text": "",
            "corrected_text": None,
            "correction_applied": False,
            "correction_status": "skipped",
        }

    text = speech_to_text(audio_bytes, file.filename)
    print("TRANSCRIPT:", text)

    if VOICE_PIPELINE_MODE == "corrected" and text:
        correction = correct_asr_text(text)
        active_text = correction.corrected_text
        corrected_text = correction.corrected_text
        correction_status = correction.status
        correction_applied = (
            correction.status == "success" and correction.corrected_text != text
        )
    else:
        active_text = text
        corrected_text = None
        correction_status = "skipped"
        correction_applied = False

    return {
        "text": active_text,
        "raw_text": text,
        "corrected_text": corrected_text,
        "correction_applied": correction_applied,
        "correction_status": correction_status,
    }

