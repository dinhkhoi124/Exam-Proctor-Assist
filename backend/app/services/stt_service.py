import tempfile
import os
from openai import OpenAI
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
STT_PROMPT = "Hội thoại hỗ trợ khắc phục sự cố tại FPT university"


def _audio_suffix(audio_bytes: bytes, filename: str) -> str:
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    if audio_bytes.startswith(b"RIFF") and audio_bytes[8:12] == b"WAVE":
        return ".wav"
    if audio_bytes.startswith(b"OggS"):
        return ".ogg"
    if audio_bytes[4:8] == b"ftyp":
        return ".m4a"
    if audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff\xfb"):
        return ".mp3"

    suffix = os.path.splitext(filename or "")[1].lower()
    return suffix if suffix in {".webm", ".wav", ".ogg", ".m4a", ".mp3", ".mp4"} else ".webm"


def speech_to_text(audio_bytes: bytes, filename: str = "recording.webm") -> str:
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=_audio_suffix(audio_bytes, filename)
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="gpt-4o-mini-transcribe",
                language="vi",
                prompt=STT_PROMPT
            )

        text = transcript.text.strip()

        if not text or text.casefold() == STT_PROMPT.casefold():
            print("Primary STT returned empty text; retrying with whisper-1")
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    language="vi"
                )
            text = transcript.text.strip()

        if not text:
            return ""

        print(f"\n🎤 STT RESULT: {text}\n")

        return text

    except Exception as e:
        print(f"\n❌ STT Error: {e}\n")
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
