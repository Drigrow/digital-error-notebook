import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB max upload

    # OpenRouter
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Admin
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

    # Encryption
    FERNET_KEY = os.getenv("FERNET_KEY", "")

    # Vision models (OpenRouter model IDs)
    VISION_MODELS = [
        {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash"},
        {"id": "qwen/qwen3.5-397b-a17b", "name": "Qwen 3.5 397B (Default)"},
    ]
    DEFAULT_VISION_MODEL = "qwen/qwen3.5-397b-a17b"

    # Chat models
    CHAT_MODELS = [
        {"id": "qwen/qwen3.5-397b-a17b", "name": "Qwen 3.5 397B (Default)"},
        {"id": "qwen/qwen3-235b-a22b-2507", "name": "Qwen 3 235B"},
        {"id": "openai/gpt-5-nano", "name": "GPT-5 Nano"},
        {"id": "openai/gpt-oss-120b:nitro", "name": "GPT OSS 120B Nitro"},
        {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash"},
    ]
    DEFAULT_CHAT_MODEL = "qwen/qwen3.5-397b-a17b"

    # Limited models for users without their own API key
    LIMITED_MODELS = [
        {"id": "openai/gpt-5-nano", "name": "GPT-5 Nano"},
        {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash"},
    ]

    # Quota defaults
    DEFAULT_QUOTA_CHAT = 50
    DEFAULT_QUOTA_IMAGES = 20
    DEFAULT_QUOTA_QUIZZES = 10
    QUOTA_REFRESH_HOURS = 6
