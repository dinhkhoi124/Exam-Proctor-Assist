import os
from dotenv import load_dotenv

load_dotenv()

# =========================
# OPENAI (RAG)
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in .env")

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

# =========================
# EMAIL CONFIG
# =========================
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_TLS = os.getenv("MAIL_TLS", "True") == "True"
MAIL_SSL = os.getenv("MAIL_SSL", "False") == "True"

# Chỉ kiểm tra email nếu bạn thực sự bật tính năng gửi mail
if MAIL_USERNAME and not MAIL_PASSWORD:
    raise RuntimeError("MAIL_PASSWORD is missing in .env")