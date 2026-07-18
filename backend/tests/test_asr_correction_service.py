from types import SimpleNamespace

from app.services.asr_correction_service import correct_asr_text
from app.prompts.asr_correction import ASR_CORRECTION_SYSTEM_PROMPT


class FakeCompletions:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4),
        )


def fake_client(completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_correction_returns_text_and_usage():
    completions = FakeCompletions("Nội quy kỳ thi")
    result = correct_asr_text(
        "nội huy kỳ thi", openai_client=fake_client(completions)
    )
    assert result.corrected_text == "Nội quy kỳ thi"
    assert result.status == "success"
    assert result.prompt_tokens == 12
    assert completions.calls[0]["temperature"] == 0


def test_correction_falls_back_on_api_error():
    result = correct_asr_text(
        "Giữ nguyên E360 và mã 123",
        openai_client=fake_client(FakeCompletions(error=RuntimeError("offline"))),
    )
    assert result.corrected_text == "Giữ nguyên E360 và mã 123"
    assert result.status == "fallback"


def test_empty_input_skips_api_call():
    completions = FakeCompletions("unused")
    result = correct_asr_text("  ", openai_client=fake_client(completions))
    assert result.status == "skipped"
    assert completions.calls == []


def test_prompt_requires_minimal_edits_and_preserves_valid_domain_tokens():
    assert "COPY là mặc định" in ASR_CORRECTION_SYSTEM_PROMPT
    assert "đổi từ đồng nghĩa" in ASR_CORRECTION_SYSTEM_PROMPT
    assert "mở rộng dạng hợp lệ như pass, SV, GT" in ASR_CORRECTION_SYSTEM_PROMPT
    assert 'đổi "sinh viên" thành Student/Students' in ASR_CORRECTION_SYSTEM_PROMPT
    assert "tài khoản WiFi Student liên quan gì đến EOS/PEA" in ASR_CORRECTION_SYSTEM_PROMPT
