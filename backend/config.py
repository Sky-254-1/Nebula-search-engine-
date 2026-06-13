import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ioismaster:secret@db:5432/ioismain")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")