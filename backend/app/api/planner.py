"""Content planner: save an opportunity, move it idea -> scripted -> published (and start tracking its performance)."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api import validation
from app.db.mongodb import DatabaseUnavailable, get_db
from app.services.progress import now

router = APIRouter(prefix="/api/planner", tags=["Planner"])
STATUSES = ["idea", "scripted", "published"]
USER_ID = "default"          # single local user; the `users` collection is the owner of every plan item


def _db():
    try:
        db = get_db()
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    if not db.users.find_one({"_id": USER_ID}):
        db.users.insert_one({"_id": USER_ID, "name": "Local creator", "created_at": now()})
    return db


def _out(d: dict) -> dict:
    d["id"] = d.pop("_id")
    return d


class NewItem(BaseModel):
    opportunity_id: str
    title: Optional[str] = Field(None, max_length=200)
    format: Optional[str] = Field(None, max_length=60)
    brief: Optional[dict] = None          # a content brief generated in Creator Studio


@router.post("")
def create(req: NewItem):
    db = _db()
    o = db.opportunities.find_one({"_id": req.opportunity_id})
    if not o:
        raise HTTPException(404, "Opportunity not found.")
    brief = req.brief or {}
    rec = o.get("recommendation") or {}
    item = {"_id": uuid.uuid4().hex, "user_id": USER_ID, "opportunity_id": o["_id"], "analysis_id": o["analysis_id"], "topic": o["topic"],
            "title": req.title or brief.get("title") or rec.get("title") or o["topic"], "format": req.format or brief.get("format") or rec.get("content_format"),
            "status": "scripted" if brief.get("script") else "idea", "notes": "", "script": brief.get("script"), "brief": brief or None,
            "ghostgap": o["scores"]["ghostgap"], "created_at": now(), "updated_at": now(), "video_url": None, "validation_id": None}
    db.plan_items.insert_one(item)
    return _out(item)


@router.get("")
def list_items():
    items = [_out(d) for d in _db().plan_items.find({"user_id": USER_ID}).sort("updated_at", -1)]
    return {"statuses": STATUSES, "items": items}


class Patch(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=5000)
    script: Optional[str] = Field(None, max_length=40000)
    status: Optional[str] = None


@router.patch("/{item_id}")
def update(item_id: str, p: Patch):
    db = _db()
    if not db.plan_items.find_one({"_id": item_id}):
        raise HTTPException(404, "Plan item not found.")
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    if fields.get("status") not in (None, *STATUSES):
        raise HTTPException(422, f"status must be one of {STATUSES}. Use the publish action to mark an item as published.")
    if fields.get("status") == "published":
        raise HTTPException(422, "Use POST /api/planner/{id}/publish (it records the video URL and starts performance tracking).")
    db.plan_items.update_one({"_id": item_id}, {"$set": {**fields, "updated_at": now()}})
    return _out(db.plan_items.find_one({"_id": item_id}))


class Publish(BaseModel):
    video_url: str = Field(max_length=300)


@router.post("/{item_id}/publish")
def publish(item_id: str, req: Publish):
    """Mark as published, attach the video URL and start closed-loop tracking against the predicted score."""
    db = _db()
    item = db.plan_items.find_one({"_id": item_id})
    if not item:
        raise HTTPException(404, "Plan item not found.")
    opp = db.opportunities.find_one({"_id": item["opportunity_id"]})
    if not opp:
        raise HTTPException(404, "The opportunity behind this item no longer exists.")
    v = validation.create_tracking(opp, req.video_url, plan_item_id=item_id)
    db.plan_items.update_one({"_id": item_id}, {"$set": {"status": "published", "video_url": req.video_url, "validation_id": v["_id"], "updated_at": now()}})
    return _out(db.plan_items.find_one({"_id": item_id}))


@router.delete("/{item_id}")
def delete(item_id: str):
    return {"deleted": _db().plan_items.delete_one({"_id": item_id}).deleted_count}
