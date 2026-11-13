from fastapi import APIRouter
from app.config import settings
from app.db.mongodb import db_status
from app.services import gemini_service, vector_service, whisper_service

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
def health():
    """Honest system state - the UI uses this instead of claiming integrations are active."""
    try:
        try:
            import sentence_transformers  # noqa: F401
            emb = {"available": True, "model": settings.embedding_model}
        except Exception:
            emb = {"available": False, "reason": "sentence-transformers not installed"}

        try:
            mongo = db_status()
            if not isinstance(mongo, dict):
                mongo = {"connected": False, "reason": str(mongo)}
        except Exception as exc:
            mongo = {"connected": False, "reason": str(exc)}

        backend_type = (
            mongo.get("backend")
            or mongo.get("database")
            or mongo.get("type")
            or ("mongodb" if mongo.get("connected") else "local")
        )

        try:
            vector_backend = vector_service.backend_name()
        except Exception:
            vector_backend = "none"

        try:
            whisper_ok = whisper_service.available()
        except Exception:
            whisper_ok = False

        try:
            g = gemini_service.is_configured()
        except Exception:
            g = False

        try:
            yt_configured = settings.youtube_configured
        except Exception:
            yt_configured = False

        try:
            reddit_configured = settings.reddit_configured
        except Exception:
            reddit_configured = False

        return {
            "status": "ok",
            "demo_mode": True,
            "database": backend_type,
            "mongodb": mongo,
            "embeddings": emb,
            "clustering": {"available": True, "method": "HDBSCAN"},
            "vector_store": {"available": True, "backend": vector_backend},
            "whisper": {
                "available": whisper_ok,
                "message": "Whisper ready" if whisper_ok else "Audio/video transcription unavailable",
            },
            "gemini": {
                "configured": g,
                "message": "Gemini configured" if g else "Gemini not configured",
            },
            "youtube": {
                "configured": yt_configured,
                "message": "YouTube API connected" if yt_configured else "YouTube API not connected",
            },
            "reddit": {
                "configured": reddit_configured,
                "message": "Reddit connected" if reddit_configured else "Reddit integration unavailable",
            },
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "demo_mode": True,
            "database": "local",
            "mongodb": {"connected": False, "reason": str(exc)},
            "embeddings": {"available": False, "reason": "sentence-transformers not installed"},
            "clustering": {"available": True, "method": "HDBSCAN"},
            "vector_store": {"available": False, "backend": "none"},
            "whisper": {"available": False, "message": "Audio/video transcription unavailable"},
            "gemini": {"configured": False, "message": "Gemini not configured"},
            "youtube": {"configured": False, "message": "YouTube API not connected"},
            "reddit": {"configured": False, "message": "Reddit integration unavailable"},
        }
