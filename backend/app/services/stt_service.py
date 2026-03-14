import tempfile
import os
from openai import OpenAI
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def speech_to_text(audio_bytes: bytes, filename: str = "recording.webm") -> str:
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="gpt-4o-mini-transcribe",
                language="vi",
                prompt="Hội thoại hỗ trợ khắc phục sự cố tại FPT university"
            )

        text = transcript.text.strip()

        # 🔹 Fix trường hợp không nói gì
        if text == "" or text.lower() == "hội thoại hỗ trợ khắc phục sự cố tại fpt university":
            return ""

        print(f"\n🎤 STT RESULT: {text}\n")

        return text

    except Exception as e:
        print(f"\n❌ STT Error: {e}\n")
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)