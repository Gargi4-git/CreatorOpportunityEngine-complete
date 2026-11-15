"""LangGraph orchestration. Specialised agents share a typed state; each reads the previous agents' structured output and
adds its own. A node that sets `error` ends the run."""
import logging
import uuid
from collections import Counter

import numpy as np
from bson import Binary
from langgraph.graph import END, StateGraph

from app.agents import (competition_agent, demand_agent, explanation_agent, ghostgap_agent, ingestion_agent,
                        multimodal_agent, recommendation_agent, sentiment_agent, topic_agent, trend_agent)
from app.agents.state import PipelineState
from app.db.mongodb import DatabaseUnavailable, get_db
from app.ml.embeddings import EmbeddingUnavailable
from app.services import gemini_service, progress, vector_service

log = logging.getLogger("orchestrator")


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def persist_node(state: dict) -> dict:
    aid, records, E, opps = state["analysis_id"], state["records"], state["E"], state["opportunities"]
    db = get_db()
    progress.step(aid, "finalize", "running")
    db.audience_records.insert_many([{
        "_id": uuid.uuid4().hex, "stage": "analyzed", "analysis_id": aid, "source": r["platform"], "source_id": r.get("source_id"),
        "text": r["text"], "timestamp": r["timestamp"], "engagement": {"likes": r["likes"], "replies": r["replies"]},
        "modality": r.get("modality", "text"), "language": r.get("language"), "video_id": r.get("video_id"), "cluster_id": r["cluster_id"], "intent": r["intent"],
        "sentiment": r["sentiment"], "pain_score": r["pain_score"], "embedding_id": f"{aid}:{i}"} for i, r in enumerate(records)])
    db.embeddings.insert_many([{"_id": f"{aid}:{i}", "analysis_id": aid, "model": state["embedder_name"],
                                "vector": Binary(E[i].astype(np.float32).tobytes())} for i in range(len(records))])
    db.clusters.insert_many([{"_id": f"{aid}:{c}", "analysis_id": aid, "cluster_id": c, **{k: v for k, v in m.items()}}
                             for c, m in state["topic_meta"].items()]) if state["topic_meta"] else None
    for o in opps:
        o.pop("member_idx", None)
    if opps:
        db.opportunities.insert_many(opps)
    recs = [{"_id": uuid.uuid4().hex, "analysis_id": aid, "opportunity_id": o["_id"], "kind": "recommendation", **o["recommendation"],
             "created_at": progress.now()} for o in opps if o.get("recommendation")]
    if recs:
        db.recommendations.insert_many(recs)

    df = state["df"]
    summary = {
        "data_quality": state["report"],
        "clustering": {"method": state["clustering"]["method"], "clusters": state["clustering"]["n_clusters"],
                       "unclustered": int((state["labels"] == -1).sum())},
        "audience_comments": len(records), "total_engagement": int(df["engagement"].sum()),
        "avg_opportunity_score": _mean([o["scores"]["ghostgap"] for o in opps]),
        "avg_trend": _mean([o["scores"]["trend"] for o in opps]),
        "platforms": dict(Counter(df["platform"])), "modalities": dict(Counter(r.get("modality", "text") for r in records)),
        "components_unavailable": sorted({u for o in opps for u in o["unavailable_components"]}),
        "embedding_model": state["embedder_name"], "options": state.get("options", {}),
        "languages": state["report"].get("languages", {}), "vector_backend": vector_service.backend_name(),
        "gemini_used": any(o.get("recommendation") for o in opps) or any(m["label_source"] == "gemini" for m in state["topic_meta"].values()),
        "recommendations_generated": sum(1 for o in opps if o.get("recommendation")),
        "warnings": state.get("warnings", []),
    }
    db.analyses.update_one({"_id": aid}, {"$set": {"summary": summary, "completed_at": progress.now()}})
    progress.step(aid, "finalize", "done", "Analysis complete")
    db.analyses.update_one({"_id": aid}, {"$set": {"status": "completed", "progress": 100}})
    return {}


NODES = [("ingestion", ingestion_agent.run), ("multimodal", multimodal_agent.run), ("topic", topic_agent.run),
         ("sentiment", sentiment_agent.run), ("demand", demand_agent.run), ("trend", trend_agent.run),
         ("competition", competition_agent.run), ("ghostgap", ghostgap_agent.run),
         ("recommendation", recommendation_agent.run), ("explanation", explanation_agent.run), ("persist", persist_node)]


def build_graph():
    g = StateGraph(PipelineState)
    for name, fn in NODES:
        g.add_node(name, fn)
    g.set_entry_point(NODES[0][0])
    names = [n for n, _ in NODES]
    for a, b in zip(names, names[1:]):
        g.add_conditional_edges(a, lambda s, nxt=b: END if s.get("error") else nxt)
    g.add_edge(names[-1], END)
    return g.compile()


def run_analysis(aid: str) -> None:
    """Entry point used by the API's background task. Failures become short human-readable messages."""
    db = get_db()
    doc = db.analyses.find_one({"_id": aid})
    src, options = doc["source_ids"], doc.get("options") or {}
    try:
        final = build_graph().invoke({"analysis_id": aid, "source_ids": src, "options": options})
        if final.get("error") and final["error"] not in ("insufficient",):
            progress.fail(aid, final["error"])
    except (EmbeddingUnavailable, DatabaseUnavailable) as exc:
        progress.fail(aid, str(exc))
    except Exception:
        log.exception("analysis %s failed", aid)
        progress.fail(aid, "The analysis failed unexpectedly. Check the server log for details.")
