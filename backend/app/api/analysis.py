from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.db.mongodb import DatabaseUnavailable, get_db
from app.services.pipeline_service import create_analysis, run_analysis

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


class RunRequest(BaseModel):
    source_ids: List[str] = Field(min_length=1, max_length=10)


@router.post("/run")
def run(req: RunRequest, background: BackgroundTasks):
    try:
        db = get_db()
        found = db.sources.count_documents({"_id": {"$in": req.source_ids}})
        if found != len(set(req.source_ids)):
            raise HTTPException(404, "One or more sources were not found.")
        aid = create_analysis(req.source_ids)
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    background.add_task(run_analysis, aid)
    return {"analysis_id": aid, "status": "queued"}


@router.get("/latest")
def latest():
    try:
        doc = get_db().analyses.find_one({"status": "completed"}, sort=[("completed_at", -1)])
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    return _out(doc) if doc else {"analysis": None}


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str):
    try:
        doc = get_db().analyses.find_one({"_id": analysis_id})
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    if not doc:
        raise HTTPException(404, "Analysis not found.")
    return _out(doc)


def _out(doc):
    doc["analysis_id"] = doc.pop("_id")
    return doc
