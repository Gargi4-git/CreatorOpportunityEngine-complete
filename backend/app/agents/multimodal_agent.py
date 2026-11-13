"""AGENT 2 - MULTIMODAL. Converts text / image / audio / video-derived records into ONE unified structure so that signals
about the same problem land close together in embedding space and are clustered/fused downstream.

unified = {content, modality, topic, intent, pain_point, sentiment}
(topic/intent/pain are filled when a vision/LLM extraction already produced them at upload time; for plain text they
are produced later by the Topic and Sentiment agents.)"""
from collections import Counter

from app.services import progress


def run(state: dict) -> dict:
    aid = state["analysis_id"]
    recs = state["records"]
    mix = Counter(r.get("modality", "text") for r in recs)
    text_only = set(mix) == {"text"}
    if not text_only:
        progress.step(aid, "multimodal", "running")
    unified = []
    for r in recs:
        ai = r.get("ai") or {}
        r["embed_text"] = r["text"]
        unified.append({"content": r["text"], "modality": r.get("modality", "text"), "topic": ai.get("topic"),
                        "intent": ai.get("intent"), "pain_point": ai.get("pain_point"), "sentiment": ai.get("sentiment")})
    if text_only:
        progress.step(aid, "multimodal", "skipped", "Only text inputs - no cross-modal fusion needed")
    else:
        progress.step(aid, "multimodal", "done", "Fused modalities: " + ", ".join(f"{m}={n}" for m, n in mix.items()))
    return {"records": recs, "unified": unified}
