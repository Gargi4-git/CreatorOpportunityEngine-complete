"""AGENT 1 - INGESTION. Raw stored records -> cleaned, normalised audience records + data-quality report."""
from app.config import settings
from app.db.mongodb import get_db
from app.ml.cleaning import clean_records
from app.services import progress


def run(state: dict) -> dict:
    aid = state["analysis_id"]
    db = get_db()
    progress.step(aid, "fetch", "running")
    raw = list(db.audience_records.find({"source_ref": {"$in": state["source_ids"]}, "stage": "raw"}))[: settings.max_records]
    if not raw:
        return {"error": "No records were found for the selected source."}
    progress.step(aid, "fetch", "done", f"{len(raw)} records loaded")

    progress.step(aid, "clean", "running")
    multilingual = bool(state.get("options", {}).get("multilingual"))
    records, report = clean_records(raw, english_only=settings.english_only and not multilingual)
    if len(records) < 3:
        progress.fail(aid, "Fewer than 3 usable comments remained after cleaning - not enough data to analyze.")
        return {"error": "insufficient"}
    progress.step(aid, "clean", "done", f"{report['raw']} raw -> {len(records)} after cleaning")
    from collections import Counter
    report["languages"] = dict(Counter(r.get("language") or "unknown" for r in records))
    return {"raw": raw, "records": records, "report": report, "warnings": []}
