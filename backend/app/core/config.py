import os
from dotenv import load_dotenv

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080").rstrip("/")
FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", FRONTEND_URL).split(",")
    if origin.strip()
]

# =========================
# MODEL PROVIDERS
# =========================
# LLM and vision endpoints use the OpenAI-compatible protocol. They can point
# either to OpenAI or to a local server such as vLLM without changing code.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/") or None
LLM_API_KEY = (
    os.getenv("LLM_API_KEY")
    or OPENAI_API_KEY
    or ("local" if LLM_BASE_URL else None)
)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "2"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_FREQUENCY_PENALTY = float(os.getenv("LLM_FREQUENCY_PENALTY", "0.25"))
# vLLM supports repetition_penalty as an OpenAI-compatible extension. Keep it
# at 1.0 when switching to a provider that does not support this field.
LLM_REPETITION_PENALTY = float(os.getenv("LLM_REPETITION_PENALTY", "1.0"))
QUERY_REWRITE_MODEL = os.getenv("QUERY_REWRITE_MODEL", LLM_MODEL)

VISION_BASE_URL = (
    os.getenv("VISION_BASE_URL", "").strip().rstrip("/") or LLM_BASE_URL
)
VISION_API_KEY = (
    os.getenv("VISION_API_KEY")
    or LLM_API_KEY
    or ("local" if VISION_BASE_URL else None)
)
VISION_MODEL = os.getenv("VISION_MODEL", LLM_MODEL)
VISION_MAX_TOKENS = int(os.getenv("VISION_MAX_TOKENS", "160"))
VISION_IMAGE_MAX_DIMENSION = int(os.getenv("VISION_IMAGE_MAX_DIMENSION", "1280"))
VISION_IMAGE_JPEG_QUALITY = int(os.getenv("VISION_IMAGE_JPEG_QUALITY", "85"))
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
RAG_MAX_CONCURRENCY = int(os.getenv("RAG_MAX_CONCURRENCY", "2"))
EMBEDDING_LOCAL_FILES_ONLY = os.getenv(
    "EMBEDDING_LOCAL_FILES_ONLY", "true"
).lower() in {"1", "true", "yes"}

if LLM_MAX_CONCURRENCY < 1:
    raise RuntimeError("LLM_MAX_CONCURRENCY must be at least 1")
if RAG_MAX_CONCURRENCY < 1:
    raise RuntimeError("RAG_MAX_CONCURRENCY must be at least 1")
if VISION_IMAGE_MAX_DIMENSION < 64:
    raise RuntimeError("VISION_IMAGE_MAX_DIMENSION must be at least 64")

if not LLM_API_KEY:
    raise RuntimeError(
        "Configure LLM_API_KEY/OPENAI_API_KEY, or set LLM_BASE_URL for a local provider"
    )

# OpenAI-specific audio services remain optional while the local Faster-Whisper service is deployed.
OPENAI_STT_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
OPENAI_STT_FALLBACK_MODEL = os.getenv("OPENAI_STT_FALLBACK_MODEL", "whisper-1")
STT_BASE_URL = os.getenv("STT_BASE_URL", "").strip().rstrip("/") or None
STT_API_KEY = os.getenv("STT_API_KEY") or OPENAI_API_KEY or ("local" if STT_BASE_URL else None)
STT_MODEL = os.getenv("STT_MODEL", OPENAI_STT_MODEL)
STT_FALLBACK_MODEL = os.getenv("STT_FALLBACK_MODEL", OPENAI_STT_FALLBACK_MODEL)
STT_TIMEOUT_SECONDS = float(os.getenv("STT_TIMEOUT_SECONDS", "180"))
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "").strip() or None
VOICE_CORRECTION_ENABLED = os.getenv("VOICE_CORRECTION_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
}
VOICE_LLM_NORMALIZATION_ENABLED = os.getenv(
    "VOICE_LLM_NORMALIZATION_ENABLED", "false"
).lower() in {"1", "true", "yes"}

OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

RAG_DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
RAG_CHUNKS_DIR = os.path.join(BASE_DIR, "rag", "chunks")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "rag", "vector_store")
PROMPT_DIR = os.path.join(BASE_DIR, "prompts")

# =========================
# DATABASE
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# =========================
# JWT (LOGIN)
# =========================
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
)

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in .env")

# =========================
# RESET PASSWORD
# =========================
RESET_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("RESET_TOKEN_EXPIRE_MINUTES", 10)
)

