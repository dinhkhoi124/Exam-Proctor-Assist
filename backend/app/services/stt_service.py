import tempfile
import os
import logging
from functools import lru_cache
from openai import OpenAI
from app.core.config import (
    STT_API_KEY,
    STT_BASE_URL,
    STT_FALLBACK_MODEL,
    STT_LANGUAGE,
    STT_MODEL,
    STT_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

STT_PROMPT = (
    "FPT University, phòng thi, giám thị, sinh viên, Wi-Fi, mạng, "
    "hệ thống thi, máy tính, đăng nhập, bài thi."
)


@lru_cache(maxsize=1)
def _get_stt_client() -> OpenAI:
    if not STT_API_KEY:
        raise RuntimeError(
            "Configure STT_API_KEY/OPENAI_API_KEY, or set STT_BASE_URL for a local provider"
        )
    options = {
        "api_key": STT_API_KEY,
        "timeout": STT_TIMEOUT_SECONDS,
        "max_retries": 1,
    }
    if STT_BASE_URL:
        options["base_url"] = STT_BASE_URL
    return OpenAI(**options)


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
            request = {
                "file": audio_file,
                "model": STT_MODEL,
                "prompt": STT_PROMPT,
            }
            if STT_LANGUAGE:
                request["language"] = STT_LANGUAGE
            transcript = _get_stt_client().audio.transcriptions.create(**request)

        text = transcript.text.strip()

        if (
            STT_FALLBACK_MODEL
            and STT_FALLBACK_MODEL != STT_MODEL
            and (not text or text.casefold() == STT_PROMPT.casefold())
        ):
            logger.warning(
                "Primary STT returned empty text; retrying with %s",
                STT_FALLBACK_MODEL,
            )
            with open(tmp_path, "rb") as audio_file:
                request = {"file": audio_file, "model": STT_FALLBACK_MODEL}
                if STT_LANGUAGE:
                    request["language"] = STT_LANGUAGE
                transcript = _get_stt_client().audio.transcriptions.create(**request)
            text = transcript.text.strip()

        if not text:
            return ""

        # Do not log transcript contents: they may contain personal data.
        # Keeping logging outside terminal-specific Unicode output also prevents
        # a successful transcription from becoming a Windows cp1252 failure.
        logger.info("STT completed successfully (characters=%d)", len(text))

        return text

    except Exception as exc:
        logger.exception("STT request failed")
        raise RuntimeError("Speech-to-text service failed") from exc

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
