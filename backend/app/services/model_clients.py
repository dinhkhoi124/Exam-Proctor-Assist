from functools import lru_cache

from openai import AsyncOpenAI, OpenAI

from app.core.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_TIMEOUT_SECONDS,
    VISION_API_KEY,
    VISION_BASE_URL,
)


def _client_options(api_key: str | None, base_url: str | None) -> dict:
    options = {
        "api_key": api_key or "local",
        "timeout": LLM_TIMEOUT_SECONDS,
        "max_retries": 2,
    }
    if base_url:
        options["base_url"] = base_url
    return options


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    return OpenAI(**_client_options(LLM_API_KEY, LLM_BASE_URL))


@lru_cache(maxsize=1)
def get_async_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(**_client_options(LLM_API_KEY, LLM_BASE_URL))


@lru_cache(maxsize=1)
def get_vision_client() -> OpenAI:
    return OpenAI(**_client_options(VISION_API_KEY, VISION_BASE_URL))
