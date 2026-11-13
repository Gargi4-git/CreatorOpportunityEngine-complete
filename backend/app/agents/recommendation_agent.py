"""AGENT 9 - RECOMMENDATION (RAG). For the top opportunities:
  1. RETRIEVE the audience comments nearest to the topic centroid from the FAISS index,
  2. AUGMENT a structured prompt with that evidence + the computed statistics,
  3. GENERATE the recommendation with Gemini (validated by Pydantic),
  4. VERIFY: any cited evidence id that wasn't actually retrieved is dropped; a recommendation with no valid
     citations is rejected. The system therefore never displays evidence it did not retrieve."""
import numpy as np

from app.services import gemini_service, progress, vector_service

TOP_K = 5
RETRIEVE = 12


def run(state: dict) -> dict:
    aid, records, E, labels = state["analysis_id"], state["records"], state["E"], state["labels"]
    opps, warnings = state["opportunities"], list(state.get("warnings", []))
    vector_service.build_index(aid, E, [f"{aid}:{i}" for i in range(len(records))])  # semantic index for retrieval + later search

    if not gemini_service.is_configured():
        for o in opps:
            o["recommendation_status"] = "not_generated: Gemini not configured"
        progress.step(aid, "recommend", "skipped", "Gemini not configured - no recommendations generated")
        return {"opportunities": opps}

    progress.step(aid, "recommend", "running")
    ok = 0
    for o in opps[:TOP_K]:
        idx = np.where(labels == o["cluster_id"])[0]
        centroid = E[idx].mean(axis=0)
        centroid /= (np.linalg.norm(centroid) or 1.0)
        hits = vector_service.search_vector(aid, centroid, RETRIEVE)
        evidence = []
        for n, h in enumerate(hits, 1):
            r = records[int(h["embedding_id"].split(":")[1])]
            evidence.append({"id": n, "text": r["text"], "platform": r["platform"], "likes": r["likes"],
                             "similarity": h["score"], "in_cluster": r["cluster_id"] == o["cluster_id"]})
        try:
            rec = gemini_service.generate_recommendation(o, evidence)
        except gemini_service.GeminiError as exc:
            o["recommendation_status"] = f"failed: {exc}"
            warnings.append(f"Recommendation for '{o['topic']}': {exc}")
            continue
        valid = [i for i in rec.evidence_ids if 1 <= i <= len(evidence)]
        if not valid:
            o["recommendation_status"] = "rejected: model cited no verifiable evidence"
            continue
        d = rec.model_dump()
        d["evidence_ids"] = valid
        d["evidence"] = [evidence[i - 1] for i in valid]
        o["recommendation"], o["recommendation_status"] = d, "generated"
        o["retrieved_evidence"] = evidence
        ok += 1
    for o in opps[TOP_K:]:
        o["recommendation_status"] = f"not_generated: only the top {TOP_K} opportunities get recommendations"
    progress.step(aid, "recommend", "done" if ok else "skipped", f"{ok} recommendations generated (Gemini + RAG)")
    return {"opportunities": opps, "warnings": warnings}
