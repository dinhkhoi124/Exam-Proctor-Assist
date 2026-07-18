import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest


def test_input_type_defaults_to_text():
    assert ChatRequest(message="hello").input_type == "text"


def test_input_type_accepts_voice():
    assert ChatRequest(message="hello", input_type="voice").input_type == "voice"


def test_input_type_rejects_unknown_value():
    with pytest.raises(ValidationError):
        ChatRequest(message="hello", input_type="video")
