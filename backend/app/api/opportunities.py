from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.mongodb import DatabaseUnavailable, get_db

router = APIRouter(prefix="/api/opportunities", tags=["Opportunities"])

# sort name -> (key, reverse). Missing values always sort last.
def _num(path, missing_high=False):
    def key(o):
        v = o["scores"].get(path)
        return (v is None, -(v or 0) if not missing_high else (v or 0))
    return key


SORTS = {
    "opportunity": _num("ghostgap"),
    "demand": _num("demand"),
    "trend": _num("trend"),
    "competition": _num("competition", missing_high=True),     # lowest competition first
    "newest": lambda o: (False, o["created_at"]),
}


def _out(o):
    o["id"] = o.pop("_id")
    return o


@router.get("")
def list_opportunities(analysis_id: Optional[str] = None, q: Optional[str] = None, platform: Optional[str] = None, topic: Optional[str] = None,
                       min_score: float = Query(0, ge=0, le=100), sort: str = "opportunity"):
    if sort not in SORTS:
        raise HTTPException(400, f"sort must be one of {sorted(SORTS)}")
    try:
        db = get_db()
        if analysis_id is None:
            last = db.analyses.find_one({"status": "completed"}, sort=[("completed_at", -1)])
            if not last:
                return {"analysis_id": None, "total": 0, "opportunities": []}
            analysis_id = last["_id"]
        items = list(db.opportunities.find({"analysis_id": analysis_id}))
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    if q:
        items = [o for o in items if q.lower() in o["topic"].lower()]
    if topic:
        items = [o for o in items if o["topic"] == topic]
    if platform:
        items = [o for o in items if platform.lower() in o["platform_share"]]
    items = [o for o in items if (o["scores"]["ghostgap"] or 0) >= min_score]
    items.sort(key=SORTS[sort], reverse=(sort == "newest"))
    return {"analysis_id": analysis_id, "total": len(items), "opportunities": [_out(o) for o in items]}


@router.get("/{opp_id}")
def get_opportunity(opp_id: str):
    try:
        o = get_db().opportunities.find_one({"_id": opp_id})
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    if not o:
        raise HTTPException(404, "Opportunity not found.")
    return _out(o)
