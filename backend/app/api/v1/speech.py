from fastapi import APIRouter, UploadFile, File
from app.services.stt_service import speech_to_text
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
            "text": ""
        }

    text = speech_to_text(audio_bytes, file.filename)
    print("TRANSCRIPT:", text)

    return {
        "text": text
    }

