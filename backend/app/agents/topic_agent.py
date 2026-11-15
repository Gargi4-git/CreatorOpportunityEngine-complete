"""AGENT 3 - TOPIC. Embeddings (MiniLM) -> near-duplicate removal -> HDBSCAN clustering -> topic labels.
Labels start as deterministic TF-IDF keywords; Gemini is used ONLY to turn a cluster into a human-readable
audience-need label (and a search query for the competition agent) when configured."""
import numpy as np

from app.ml.cleaning import drop_near_duplicates
from app.ml.clustering import cluster_embeddings, label_clusters
from app.ml.embeddings import get_embedder
from app.services import gemini_service, progress
from app.ml.competition import keywords


def run(state: dict) -> dict:
    aid = state["analysis_id"]
    records, report, warnings = state["records"], state["report"], list(state.get("warnings", []))

    progress.step(aid, "embed", "running")
    multilingual = bool(state.get("options", {}).get("multilingual"))
    embedder = get_embedder(multilingual)
    E = embedder.encode([r["embed_text"] for r in records])
    records, E, near = drop_near_duplicates(records, E)
    report["near_duplicates_removed"], report["analyzed"] = near, len(records)
    progress.step(aid, "embed", "done", f"{len(records)} x {E.shape[1]}-d embeddings ({embedder.name})")

    progress.step(aid, "cluster", "running")
    texts = [r["text"] for r in records]
    cl = cluster_embeddings(E)
    labels = cl["labels"]
    kw = label_clusters(texts, labels, multilingual=multilingual)
    cluster_ids = sorted(set(int(l) for l in labels) - {-1})
    sizes = {c: int((labels == c).sum()) for c in cluster_ids}
    meta = {}
    gemini_on = gemini_service.is_configured()
    gemini_ok = 0
    for rank, c in enumerate(sorted(cluster_ids, key=lambda c: -sizes[c])):
        idx = np.where(labels == c)[0]
        centroid = E[idx].mean(axis=0)
        norm = np.linalg.norm(centroid) or 1.0
        centroid = centroid / norm
        sims = E[idx] @ centroid
        order = idx[np.argsort(-sims)]
        mods = {}
        for i in idx:
            m = records[i].get("modality", "text")
            mods[m] = mods.get(m, 0) + 1
        m = {"label": kw[c], "label_source": "keyword (TF-IDF)", "audience_need": None, "search_query": kw[c].replace(" / ", " "),
             "confidence": round(float(np.clip(sims.mean(), 0, 1)), 3), "modality_mix": mods}
        if gemini_on and rank < 10:
            try:
                t = gemini_service.label_topic([records[i]["text"] for i in order[:12]], kw[c])
                m.update(label=t.label, audience_need=t.audience_need, search_query=t.search_query, label_source="gemini")
                gemini_ok += 1
            except gemini_service.GeminiError as exc:
                warnings.append(f"Topic label for cluster {c} fell back to keywords: {exc}")
        meta[c] = m
    detail = f"{cl['n_clusters']} clusters via {cl['method']}; {int((labels == -1).sum())} unclustered"
    if gemini_on:
        detail += f"; {gemini_ok} labelled by Gemini"
    progress.step(aid, "cluster", "done", detail)
    return {"records": records, "E": E, "labels": labels, "clustering": cl, "topic_meta": meta, "cluster_ids": cluster_ids,
            "report": report, "embedder_name": embedder.name, "warnings": warnings}
