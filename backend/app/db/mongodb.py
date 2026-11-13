"""MongoDB access.

Collections: users, sources, audience_records, embeddings, clusters,
analyses, opportunities, recommendations.
"""
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings


class DatabaseUnavailable(RuntimeError):
    pass


_db: Optional[Database] = None


def set_db(db: Optional[Database]) -> None:
    """Inject a database (used by tests)."""
    global _db
    _db = db


def get_db() -> Database:
    global _db
    if _db is None:
        client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
        try:
            client.admin.command("ping")
        except Exception as exc:  # never leak connection strings / stack traces
            raise DatabaseUnavailable(
                "MongoDB is unavailable. Start MongoDB and check MONGODB_URI in your .env file."
            ) from exc
        _db = client[settings.database_name]
    return _db


def db_status() -> dict:
    try:
        get_db().list_collection_names()
        return {"connected": True}
    except Exception:
        return {"connected": False, "reason": "MongoDB unreachable - check MONGODB_URI"}
