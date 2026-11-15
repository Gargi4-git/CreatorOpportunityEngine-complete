"""Central configuration. All secrets come from environment variables (.env); none are ever sent to the frontend."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name: str = os.getenv("DATABASE_NAME", "creator_opportunity_engine")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    max_records: int = int(os.getenv("MAX_RECORDS", "5000"))
    english_only: bool = _flag("CLEAN_ENGLISH_ONLY", True)
    multilingual_model: str = os.getenv("MULTILINGUAL_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    cors_origins: tuple = tuple(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","))

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def youtube_configured(self) -> bool:
        return bool(self.youtube_api_key)

    @property
    def reddit_configured(self) -> bool:
        return bool(self.reddit_client_id and self.reddit_client_secret and self.reddit_user_agent)


settings = Settings()
