from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.mongodb import DatabaseUnavailable, get_db
from app.ml.embeddings import EmbeddingUnavailable
from app.services import vector_service

router = APIRouter(prefix="/api", tags=["Search"])


@router.get("/search")
def semantic_search(q: str = Query(min_length=2, max_length=300), analysis_id: Optional[str] = None, k: int = Query(10, ge=1, le=50)):
    """Semantic (meaning-based) search over audience records, via the FAISS index."""
    try:
        if analysis_id is None:
            last = get_db().analyses.find_one({"status": "completed"}, sort=[("completed_at", -1)])
            if not last:
                return {"results": [], "message": "No analysis yet"}
            analysis_id = last["_id"]
        return {"analysis_id": analysis_id, "backend": vector_service.backend_name(),
                "results": vector_service.semantic_search(q, analysis_id, k)}
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc))
