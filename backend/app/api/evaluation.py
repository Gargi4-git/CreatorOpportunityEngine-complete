"""Evaluation endpoints: hand-label comments, measure classifier / clustering quality, GhostGap ablation, embedder comparison."""
import io
import random
import re
import uuid
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.db.mongodb import DatabaseUnavailable, get_db
from app.ml import evaluation as ev
from app.ml.clustering import cluster_embeddings
from app.ml.embeddings import EmbeddingUnavailable, HashingEmbedder, SentenceTransformerEmbedder, get_embedder
from app.ml.sentiment import PrototypeClassifier
from app.config import settings
from app.services import analysis_loader
from app.services.progress import now

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().lower())


def _db():
    try:
        return get_db()
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))


class LabelIn(BaseModel):
    text: str = Field(min_length=3, max_length=2000)
    intent: str
    sentiment: str
    topic: Optional[str] = Field(None, max_length=80)


@router.get("/options")
def options():
    return {"intents": ev.INTENTS, "sentiments": ev.SENTIMENTS, "min_labels": ev.MIN_LABELS}


@router.get("/sample")
def sample(analysis_id: Optional[str] = None, n: int = 100):
    """Random comments to label BLIND (predictions are not shown, so the labels are unbiased)."""
    db = _db()
    aid = analysis_id or analysis_loader.latest_analysis_id()
    if not aid:
        raise HTTPException(404, "Run an analysis first, or import a labelled CSV.")
    labeled = {_norm(d["text"]) for d in db.eval_labels.find({}, {"text": 1})}
    texts = [r["text"] for r in db.audience_records.find({"analysis_id": aid, "stage": "analyzed"}) if _norm(r["text"]) not in labeled]
    random.Random().shuffle(texts)
    return {"analysis_id": aid, "remaining_unlabeled": len(texts), "items": [{"text": t} for t in texts[: max(1, min(n, 300))]]}


@router.post("/labels")
def add_labels(items: List[LabelIn]):
    db = _db()
    saved = 0
    for it in items:
        if it.intent not in ev.INTENTS or it.sentiment not in ev.SENTIMENTS:
            raise HTTPException(422, "Unknown intent or sentiment label.")
        db.eval_labels.replace_one({"key": _norm(it.text)}, {"_id": uuid.uuid4().hex, "key": _norm(it.text), "text": it.text, "intent": it.intent,
                                   "sentiment": it.sentiment, "topic": it.topic, "created_at": now()}, upsert=True)
        saved += 1
    return {"saved": saved, "total": db.eval_labels.count_documents({})}


@router.get("/labels")
def labels_summary():
    docs = list(_db().eval_labels.find({}))
    from collections import Counter
    return {"total": len(docs), "intent": dict(Counter(d["intent"] for d in docs)), "sentiment": dict(Counter(d["sentiment"] for d in docs)),
            "topics": dict(Counter(d["topic"] for d in docs if d.get("topic"))), "min_labels": ev.MIN_LABELS}


@router.delete("/labels")
def clear_labels():
    return {"deleted": _db().eval_labels.delete_many({}).deleted_count}


@router.post("/labels/import")
async def import_labels(file: UploadFile = File(...)):
    raw = await file.read(5 * 1024 * 1024)
    try:
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except Exception:
        raise HTTPException(422, "Could not read this file as CSV.")
    cols = {c.lower().strip(): c for c in df.columns}
    tcol = cols.get("comment") or cols.get("text")
    if not tcol or "intent" not in cols or "sentiment" not in cols:
        raise HTTPException(422, "CSV needs columns: comment (or text), intent, sentiment (optional: topic).")
    db, saved, skipped = _db(), 0, 0
    for _, r in df.iterrows():
        text, intent, sent = r[tcol].strip(), r[cols["intent"]].strip().lower(), r[cols["sentiment"]].strip().lower()
        if len(text) < 3 or intent not in ev.INTENTS or sent not in ev.SENTIMENTS:
            skipped += 1
            continue
        topic = (r[cols["topic"]].strip() if "topic" in cols else "") or None
        db.eval_labels.replace_one({"key": _norm(text)}, {"_id": uuid.uuid4().hex, "key": _norm(text), "text": text, "intent": intent,
                                   "sentiment": sent, "topic": topic, "created_at": now()}, upsert=True)
        saved += 1
    return {"saved": saved, "skipped_invalid": skipped, "total": db.eval_labels.count_documents({})}


def _classify(labels: list, embedder) -> dict:
    texts = [d["text"] for d in labels]
    E = embedder.encode(texts)
    pred = PrototypeClassifier(embedder).classify(E)
    return {"E": E, "intent": ev.classification_report([d["intent"] for d in labels], [p["intent"] for p in pred], ev.INTENTS),
            "sentiment": ev.classification_report([d["sentiment"] for d in labels], [p["sentiment"] for p in pred], ev.SENTIMENTS)}


@router.get("/report")
def report(analysis_id: Optional[str] = None):
    db = _db()
    aid = analysis_id or analysis_loader.latest_analysis_id()
    labels = list(db.eval_labels.find({}))
    out = {"analysis_id": aid, "labels": {"n": len(labels)}, "embedder": None}
    try:
        emb = get_embedder()
        out["embedder"] = emb.name
        if len(labels) >= ev.MIN_LABELS:
            c = _classify(labels, emb)
            out["classification"] = {"available": True, "intent": c["intent"], "sentiment": c["sentiment"],
                                     "note": "Predictions come from the same embedding-prototype classifier the pipeline uses."}
            topics = [d.get("topic") for d in labels]
            tl = [i for i, t in enumerate(topics) if t]
            out["topic_recovery"] = ev.topic_recovery(c["E"][tl], [topics[i] for i in tl]) if len(tl) >= 10 else None
        else:
            out["classification"] = {"available": False, "reason": f"Label at least {ev.MIN_LABELS} comments (have {len(labels)}) to compute accuracy."}
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc))
    if aid:
        try:
            E, cl, _ = analysis_loader.load_matrix(aid)
            out["clustering"] = ev.clustering_quality(E, cl)
        except LookupError:
            out["clustering"] = None
        opps = list(db.opportunities.find({"analysis_id": aid}))
        if len(opps) >= 3:
            out["ablation"] = ev.ablation([o["scores"] for o in opps], [o["topic"] for o in opps])
        else:
            out["ablation"] = {"available": False, "reason": "Need at least 3 topics for a ranking ablation."}
    return out


@router.post("/compare-embedders")
def compare_embedders(analysis_id: Optional[str] = None):
    """Same labelled comments + same analysis texts through each embedder: accuracy, silhouette, clusters, and cluster agreement."""
    db = _db()
    aid = analysis_id or analysis_loader.latest_analysis_id()
    if not aid:
        raise HTTPException(404, "Run an analysis first.")
    labels = list(db.eval_labels.find({}))
    texts = [r["text"] for r in db.audience_records.find({"analysis_id": aid, "stage": "analyzed"})][:800]
    candidates = [("primary", get_embedder())]
    if not isinstance(candidates[0][1], HashingEmbedder):
        candidates.append(("baseline", HashingEmbedder()))
    results, clusterings = [], {}
    for role, emb in candidates:
        row = {"role": role, "name": emb.name}
        try:
            Et = emb.encode(texts)
            cl = cluster_embeddings(Et)
            clusterings[role] = cl["labels"]
            row["clustering"] = {**ev.clustering_quality(Et, cl["labels"]), "method": cl["method"]}
            if len(labels) >= ev.MIN_LABELS:
                c = _classify(labels, emb)
                row["intent_accuracy"], row["intent_macro_f1"] = c["intent"]["accuracy"], c["intent"]["macro_f1"]
                row["sentiment_accuracy"], row["sentiment_macro_f1"] = c["sentiment"]["accuracy"], c["sentiment"]["macro_f1"]
            results.append(row)
        except EmbeddingUnavailable as exc:
            results.append({**row, "available": False, "reason": str(exc)})
    out = {"analysis_id": aid, "n_texts": len(texts), "n_labels": len(labels), "embedders": results}
    if len(clusterings) == 2:
        out["cluster_agreement"] = ev.agreement(clusterings["primary"], clusterings["baseline"])
    if len(labels) < ev.MIN_LABELS:
        out["note"] = f"Label at least {ev.MIN_LABELS} comments to compare classification accuracy too."
    return out
