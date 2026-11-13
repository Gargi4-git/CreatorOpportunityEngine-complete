"""AGENT 4 - SENTIMENT / INTENT. Embedding-prototype zero-shot classifier for every record. Where a vision/LLM extraction
already exists (image/audio-derived records) its structured fields take precedence."""
import pandas as pd

from app.ml.embeddings import get_embedder
from app.ml.sentiment import PrototypeClassifier
from app.services import progress


def run(state: dict) -> dict:
    aid = state["analysis_id"]
    records, E, labels = state["records"], state["E"], state["labels"]
    progress.step(aid, "intent", "running")
    cls = PrototypeClassifier(get_embedder()).classify(E)
    overridden = 0
    for i, r in enumerate(records):
        r.update(cls[i])
        ai = r.get("ai") or {}
        if ai.get("intent"):
            r["intent"] = str(ai["intent"]).lower().replace(" ", "_")
            overridden += 1
        if ai.get("sentiment") in ("positive", "negative", "neutral"):
            r["sentiment"] = ai["sentiment"]
        r["cluster_id"] = int(labels[i])
        r["engagement"] = int(r.get("likes", 0)) + int(r.get("replies", 0))
    df = pd.DataFrame([{k: r[k] for k in ("platform", "timestamp", "engagement", "cluster_id")} for r in records])
    progress.step(aid, "intent", "done", "embedding-prototype zero-shot classification"
                  + (f"; {overridden} records used vision/LLM extraction" if overridden else ""))
    return {"records": records, "df": df, "classification": cls}
