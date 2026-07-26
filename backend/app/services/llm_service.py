import base64
import binascii
from collections import Counter
import logging
import re

from app.core.config import (
    LLM_FREQUENCY_PENALTY,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_REPETITION_PENALTY,
    LLM_TEMPERATURE,
    QUERY_REWRITE_MODEL,
    VISION_MAX_TOKENS,
    VISION_MODEL,
)
from app.prompts.exam_support import SYSTEM_PROMPT
from app.services.model_clients import get_llm_client, get_vision_client

logger = logging.getLogger(__name__)

_QUERY_PROTECTED_TERMS = (
    "khảo thí",
    "phòng thi",
    "giám thị",
    "FPT",
    "USB",
    "Wi-Fi",
    "PEA",
    "PEALogin",
    "EOS",
    "EOSClient",
)


def _response_text(response) -> str:
    return (response.choices[0].message.content or "").strip()


def _preserves_query_terms(source: str, rewritten: str) -> bool:
    source_folded = source.casefold()
    rewritten_folded = rewritten.casefold()
    return all(
        term.casefold() not in source_folded or term.casefold() in rewritten_folded
        for term in _QUERY_PROTECTED_TERMS
    )


def _has_repeated_sequence(text: str) -> bool:
    """Detect a repeated 3-8 word cycle without flagging ordinary list prose."""
    tokens = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
    if len(tokens) < 24:
        return False

    for size in range(3, 9):
        counts = Counter(
            tuple(tokens[index:index + size])
            for index in range(len(tokens) - size + 1)
        )
        most_common_count = max(counts.values(), default=0)
        repeated_token_count = most_common_count * size
        if most_common_count >= 4 and repeated_token_count >= max(18, len(tokens) // 4):
            return True
    return False


def _create_answer_completion(
    user_content: list[dict],
    frequency_penalty: float,
    repetition_penalty: float,
    retry: bool = False,
):
    system_prompt = SYSTEM_PROMPT
    if retry:
        system_prompt += (
            "\nKhông lặp lại từ, phím tắt hoặc một chuỗi nội dung nhiều lần. "
            "Nếu dữ liệu dạng bảng không rõ thứ tự, hãy mô tả ngắn gọn và yêu cầu "
            "người dùng đối chiếu bảng trong trang tài liệu được trích dẫn."
        )

    request_options = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": LLM_TEMPERATURE,
        "frequency_penalty": frequency_penalty,
        "max_tokens": LLM_MAX_TOKENS,
    }
    if repetition_penalty != 1.0:
        request_options["extra_body"] = {
            "repetition_penalty": repetition_penalty,
        }

    return get_llm_client().chat.completions.create(**request_options)


def _image_data_url(image_base64: str) -> str:
    if image_base64.startswith("data:"):
        return image_base64

    clean_base64 = image_base64.strip()
    mime_type = "image/jpeg"
    try:
        header = base64.b64decode(clean_base64[:64], validate=False)
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
        elif header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            mime_type = "image/webp"
        elif header.startswith((b"GIF87a", b"GIF89a")):
            mime_type = "image/gif"
    except (binascii.Error, ValueError):
        pass

    return f"data:{mime_type};base64,{clean_base64}"


def extract_image_text(image_base64: str) -> str:
    """Extract only visible error codes/messages for retrieval query creation."""
    response = get_vision_client().chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là bộ OCR cho hệ thống hỗ trợ coi thi. Chỉ trích xuất nguyên văn "
                    "mã lỗi hoặc thông báo lỗi nhìn thấy rõ trong ảnh. Không giải thích, "
                    "không đưa ra cách xử lý. Nếu không thấy nội dung rõ ràng, trả về None."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Trích xuất mã lỗi hoặc thông báo lỗi trong ảnh này.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": _image_data_url(image_base64)},
                    },
                ],
            },
        ],
        temperature=0,
        max_tokens=VISION_MAX_TOKENS,
    )
    return _response_text(response)


def rewrite_query(user_input: str, image_ocr: str | None = None) -> str:
    original_query = " ".join(part for part in (user_input, image_ocr or "") if part).strip()
    rewrite_prompt = f"""
    Bạn là chuyên gia điều phối dữ liệu RAG.
    Nhiệm vụ: Tạo ra một Search Query ĐƠN NHẤT và CHÍNH XÁC NHẤT.

    [NGỮ CẢNH]
    - Nếu có lỗi từ ảnh: {image_ocr if image_ocr else "Không"}
    - Câu hỏi Giám thị: {user_input}

    [CHIẾN LƯỢC TÌM KIẾM]
    1. Nếu có lỗi từ ảnh: Ưu tiên tìm kiếm các tài liệu liên quan đến mã lỗi đó.
    2. Ưu tiên tìm các ảnh tài liệu hướng dẫn liên quan đến câu trả lời.
    3. Nếu Giám thị hỏi về mật khẩu: CHỈ tìm 'hướng dẫn đổi mật khẩu wifi portal'.
    4. TUYỆT ĐỐI không trộn lẫn các từ khóa 'wifi', 'mạng', 'vpn' nếu mục tiêu là 'mật khẩu'.
    5. Khi có câu hỏi liên quan đến "mật khẩu wifi fu-exam" thì tìm "hướng dẫn kết nối wifi fu-exam".
    6. Giữ nguyên tuyệt đối mọi thuật ngữ xuất hiện trong câu hỏi, đặc biệt: khảo thí,
       phòng thi, giám thị, FPT, USB, Wi-Fi, PEA, PEALogin, EOS và EOSClient.
    Trả về DUY NHẤT search query:"""

    try:
        response = get_llm_client().chat.completions.create(
            model=QUERY_REWRITE_MODEL,
            messages=[{"role": "user", "content": rewrite_prompt}],
            temperature=0,
            max_tokens=160,
        )
        rewritten = _response_text(response)
        if not rewritten or not _preserves_query_terms(original_query, rewritten):
            logger.warning("Query rewrite changed a protected term; using the original query")
            return original_query
        return rewritten
    except Exception as exc:
        logger.warning(
            "Query rewrite failed; using the original query",
            exc_info=exc,
        )
        return original_query


def generate_answer(prompt: str, image_base64: str | None = None) -> str:
    user_content = [{"type": "text", "text": prompt}]
    if image_base64:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": _image_data_url(image_base64)},
            }
        )

    response = _create_answer_completion(
        user_content,
        frequency_penalty=LLM_FREQUENCY_PENALTY,
        repetition_penalty=LLM_REPETITION_PENALTY,
    )
    answer = _response_text(response)
    finish_reason = response.choices[0].finish_reason

    if finish_reason == "length" and _has_repeated_sequence(answer):
        logger.warning(
            "Detected repetitive LLM output at the token limit; retrying once "
            "with stronger penalties"
        )
        response = _create_answer_completion(
            user_content,
            frequency_penalty=max(LLM_FREQUENCY_PENALTY, 0.5),
            repetition_penalty=max(LLM_REPETITION_PENALTY, 1.12),
            retry=True,
        )
        answer = _response_text(response)

    return answer
