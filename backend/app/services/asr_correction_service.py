"""Dedicated, voice-only LLM correction service for ASR transcripts."""

from dataclasses import asdict, dataclass
import logging
from time import perf_counter
from typing import Any, Optional

from openai import OpenAI

from app.core.config import (
    ASR_CORRECTION_MODEL,
    ASR_CORRECTION_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
)
from app.prompts.asr_correction import (
    ASR_CORRECTION_SYSTEM_PROMPT,
    build_asr_correction_prompt,
)

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)


@dataclass(frozen=True)
class ASRCorrectionResult:
    corrected_text: str
    status: str
    latency_ms: int
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    error: Optional[str] = None

    def to_log_record(self, audio_id: Optional[str], raw_transcript: str) -> dict:
        return {
            "audio_id": audio_id,
            "raw_transcript": raw_transcript,
            **asdict(self),
        }


def _usage_value(usage: Any, name: str) -> Optional[int]:
    value = getattr(usage, name, None) if usage is not None else None
    return int(value) if value is not None else None


def correct_asr_text(
    raw_transcript: str,
    *,
    audio_id: Optional[str] = None,
    openai_client: Optional[Any] = None,
) -> ASRCorrectionResult:
    """Correct an ASR transcript without adding intent; fall back to raw text."""
    raw_text = (raw_transcript or "").strip()
    if not raw_text:
        return ASRCorrectionResult(
            corrected_text="",
            status="skipped",
            latency_ms=0,
            model=ASR_CORRECTION_MODEL,
        )

    started = perf_counter()
    selected_client = openai_client or client
    try:
        response = selected_client.chat.completions.create(
            model=ASR_CORRECTION_MODEL,
            messages=[
                {"role": "system", "content": ASR_CORRECTION_SYSTEM_PROMPT},
                {"role": "user", "content": build_asr_correction_prompt(raw_text)},
            ],
            temperature=0,
            timeout=ASR_CORRECTION_TIMEOUT_SECONDS,
        )
        corrected_text = (response.choices[0].message.content or "").strip()
        if not corrected_text:
            raise ValueError("ASR correction returned empty text")

        result = ASRCorrectionResult(
            corrected_text=corrected_text,
            status="success",
            latency_ms=int((perf_counter() - started) * 1000),
            model=ASR_CORRECTION_MODEL,
            prompt_tokens=_usage_value(getattr(response, "usage", None), "prompt_tokens"),
            completion_tokens=_usage_value(
                getattr(response, "usage", None), "completion_tokens"
            ),
        )
    except Exception as exc:
        logger.exception("ASR correction failed; using raw transcript")
        result = ASRCorrectionResult(
            corrected_text=raw_text,
            status="fallback",
            latency_ms=int((perf_counter() - started) * 1000),
            model=ASR_CORRECTION_MODEL,
            error=str(exc),
        )

    logger.info(
        "asr_correction",
        extra={"asr_correction": result.to_log_record(audio_id, raw_text)},
    )
    return result
