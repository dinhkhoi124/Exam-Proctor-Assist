import logging
import re

from app.core.config import QUERY_REWRITE_MODEL, VOICE_LLM_NORMALIZATION_ENABLED
from app.services.model_clients import get_async_llm_client


logger = logging.getLogger(__name__)


class VoiceCorrectionService:
    """Conservatively normalize a transcript before it becomes a RAG input."""

    _COMMON_FIXES = {
        "phòng thu": "phòng thi",
        "phòng thử": "phòng thi",
        "giám thi": "giám thị",
        "giam thi": "giám thị",
        "wifi": "Wi-Fi",
        "usb": "USB",
    }
    _PROTECTED_TERMS = (
        "khảo thí",
        "USB",
        "Wi-Fi",
        "FPT",
        "PEA",
        "PEALogin",
        "EOS",
        "EOSClient",
    )

    def __init__(self):
        self.client = get_async_llm_client() if VOICE_LLM_NORMALIZATION_ENABLED else None

    @classmethod
    def _apply_common_fixes(cls, text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        for wrong, correct in cls._COMMON_FIXES.items():
            normalized = re.sub(
                rf"\b{re.escape(wrong)}\b",
                correct,
                normalized,
                flags=re.IGNORECASE,
            )
        return normalized

    @classmethod
    def _preserves_protected_terms(cls, source: str, corrected: str) -> bool:
        source_folded = source.casefold()
        corrected_folded = corrected.casefold()
        return all(
            term.casefold() not in source_folded or term.casefold() in corrected_folded
            for term in cls._PROTECTED_TERMS
        )

    async def fix_voice_query(self, text: str) -> str:
        candidate = self._apply_common_fixes(text)
        if not candidate:
            return ""
        if not VOICE_LLM_NORMALIZATION_ENABLED:
            return candidate

        try:
            response = await self.client.chat.completions.create(
                model=QUERY_REWRITE_MODEL,
                temperature=0,
                max_tokens=96,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn chuẩn hóa transcript tiếng Việt cho chatbot hỗ trợ "
                            "giám thị phòng thi FPT University. Chỉ trả về transcript "
                            "đã sửa, không giải thích, không markdown."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"""Sửa lỗi nghe nhầm/chính tả nếu chắc chắn, đặc biệt các thuật ngữ:
- phòng thi, giám thị, sinh viên, nội quy, khảo thí, USB, Wi-Fi, hệ thống thi, máy tính, đăng nhập, bài thi.

Giữ nguyên ý, thông tin và mức độ chắc chắn của câu. Không tự thêm sự cố, bước xử lý, câu hỏi hay chi tiết không có trong transcript.
Không thay thế hoặc bỏ các mã/từ khóa kỹ thuật; USB phải luôn giữ là USB, Wi-Fi phải luôn giữ là Wi-Fi.
"khảo thí" là thuật ngữ nghiệp vụ và phải luôn được giữ nguyên chính xác.
Nếu không chắc, giữ nguyên từ gốc.

Transcript:
{candidate}""",
                    },
                ],
            )
        except Exception:
            logger.exception("Voice normalization failed; using rule-normalized transcript")
            return candidate

        corrected = (response.choices[0].message.content or "").strip()
        if not corrected or not self._preserves_protected_terms(candidate, corrected):
            logger.warning("Voice normalization changed a protected term; using original transcript")
            return candidate
        return corrected
