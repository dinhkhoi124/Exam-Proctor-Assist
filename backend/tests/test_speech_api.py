import asyncio
from types import SimpleNamespace

from app.api.v1 import speech


class FakeUpload:
    filename = "sample.wav"

    async def read(self):
        return b"R" * 9000


def test_baseline_returns_raw_without_correction(monkeypatch):
    monkeypatch.setattr(speech, "VOICE_PIPELINE_MODE", "baseline")
    monkeypatch.setattr(speech, "speech_to_text", lambda *_args: "nội huy")
    called = False

    def correction(_text):
        nonlocal called
        called = True

    monkeypatch.setattr(speech, "correct_asr_text", correction)
    result = asyncio.run(speech.stt(FakeUpload()))
    assert result["text"] == "nội huy"
    assert result["corrected_text"] is None
    assert result["correction_status"] == "skipped"
    assert called is False


def test_corrected_mode_calls_correction_once(monkeypatch):
    monkeypatch.setattr(speech, "VOICE_PIPELINE_MODE", "corrected")
    monkeypatch.setattr(speech, "speech_to_text", lambda *_args: "nội huy")
    calls = []

    def correction(text):
        calls.append(text)
        return SimpleNamespace(corrected_text="nội quy", status="success")

    monkeypatch.setattr(speech, "correct_asr_text", correction)
    result = asyncio.run(speech.stt(FakeUpload()))
    assert result["text"] == "nội quy"
    assert result["raw_text"] == "nội huy"
    assert result["correction_applied"] is True
    assert calls == ["nội huy"]
