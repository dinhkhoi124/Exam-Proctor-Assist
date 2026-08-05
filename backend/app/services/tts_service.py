from functools import lru_cache
from openai import OpenAI
from app.core.config import OPENAI_API_KEY, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE


@lru_cache(maxsize=1)
def _get_openai_audio_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for the current TTS provider")
    return OpenAI(api_key=OPENAI_API_KEY)

def text_to_speech(text: str) -> bytes:
    """
    Convert text to speech (Vietnamese)
    """
    response = _get_openai_audio_client().audio.speech.create(
        model=OPENAI_TTS_MODEL,
        voice=OPENAI_TTS_VOICE,
        input=text
    )

    return response.read()
