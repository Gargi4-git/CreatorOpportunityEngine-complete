import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongodb import DatabaseUnavailable, get_db
from app.services import gemini_service
from app.services.progress import now

router = APIRouter(prefix="/api/creator-studio", tags=["Creator Studio"])
FORMATS = {"youtube": "YouTube long-form video", "shorts": "YouTube Shorts (under 60s)", "reel": "Instagram Reel",
           "blog": "Blog post", "linkedin": "LinkedIn post"}


class GenerateRequest(BaseModel):
    opportunity_id: str
    format: Literal["youtube", "shorts", "reel", "blog", "linkedin"] = "youtube"


@router.post("/generate")
def generate(req: GenerateRequest):
    try:
        db = get_db()
        o = db.opportunities.find_one({"_id": req.opportunity_id})
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    if not o:
        raise HTTPException(404, "Opportunity not found.")
    src = o.get("retrieved_evidence") or [{"id": i + 1, "text": c["text"], "platform": c["platform"], "likes": c["likes"]}
                                          for i, c in enumerate(o["representative_comments"])]
    try:
        brief = gemini_service.generate_content_brief(o, src, FORMATS[req.format])
    except gemini_service.GeminiNotConfigured as exc:
        raise HTTPException(503, str(exc))
    except gemini_service.GeminiError as exc:
        raise HTTPException(502, str(exc))
    valid = [i for i in brief.evidence_ids if 1 <= i <= len(src)]
    out = brief.model_dump()
    out["evidence_ids"], out["evidence"] = valid, [src[i - 1] for i in valid]
    db.recommendations.insert_one({"_id": uuid.uuid4().hex, "opportunity_id": o["_id"], "analysis_id": o["analysis_id"],
                                   "kind": "content_brief", "format": req.format, "created_at": now(), **out})
    return {"opportunity_id": o["_id"], "topic": o["topic"], "format": req.format, "brief": out,
            "video_generation": {"available": False, "message": "Video generation unavailable"}}
