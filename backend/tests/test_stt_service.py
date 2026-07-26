from types import SimpleNamespace
from unittest.mock import patch

from app.services import stt_service


class _FakeTranscriptions:
    def create(self, **_request):
        return SimpleNamespace(text="Kiểm tra phòng thi.")


class _FakeSTTClient:
    audio = SimpleNamespace(transcriptions=_FakeTranscriptions())


def test_successful_stt_does_not_depend_on_terminal_unicode(monkeypatch):
    monkeypatch.setattr(stt_service, "_get_stt_client", lambda: _FakeSTTClient())

    # A successful request must not fail merely because the host terminal
    # cannot encode an emoji or the transcript contents.
    with patch("builtins.print", side_effect=UnicodeEncodeError("cp1252", "🎤", 0, 1, "")):
        result = stt_service.speech_to_text(
            b"RIFF\x00\x00\x00\x00WAVEtest-audio",
            "recording.wav",
        )

    assert result == "Kiểm tra phòng thi."
