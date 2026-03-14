from sqlalchemy import create_engine
from app.core.config import DATABASE_URL

try:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    print("✅ Database connected successfully!")
    connection.close()
except Exception as e:
    print("❌ Database connection failed:", e)