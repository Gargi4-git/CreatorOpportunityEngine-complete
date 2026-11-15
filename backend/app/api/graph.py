"""Knowledge graph: Source -> Topic -> Pain point, Topic -> Opportunity -> Content. Built with networkx from real analysis data."""
from collections import Counter
from typing import Optional

import networkx as nx
from fastapi import APIRouter, HTTPException

from app.db.mongodb import DatabaseUnavailable, get_db
from app.ml.phrases import key_phrases
from app.services import analysis_loader

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])
PAIN_THRESHOLD = 0.5


@router.get("")
def graph(analysis_id: Optional[str] = None, max_topics: int = 12):
    try:
        db = get_db()
        aid = analysis_id or analysis_loader.latest_analysis_id()
        if not aid:
            return {"has_data": False, "message": "No analysis yet"}
        opps = sorted(db.opportunities.find({"analysis_id": aid}), key=lambda o: o.get("rank", 99))[:max_topics]
        recs = list(db.audience_records.find({"analysis_id": aid, "stage": "analyzed"}))
        plan = {p["opportunity_id"]: p for p in db.plan_items.find({"analysis_id": aid})}
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))

    G = nx.DiGraph()
    nodes = {}

    def node(nid, ntype, label, value=1.0, **extra):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "label": label, "value": value, **extra}
            G.add_node(nid)
        return nid

    by_cluster = {}
    for r in recs:
        by_cluster.setdefault(r["cluster_id"], []).append(r)

    for o in opps:
        tid = node(f"topic:{o['cluster_id']}", "topic", o["topic"], o["evidence_count"], opportunity_id=o["_id"], score=o["scores"]["ghostgap"])
        for plat, n in o["platform_counts"].items():
            sid = node(f"source:{plat}", "source", plat, 1)
            G.add_edge(sid, tid, weight=n, kind="mentions")
            nodes[sid]["value"] += n
        pain_texts = [r["text"] for r in by_cluster.get(o["cluster_id"], []) if r.get("pain_score", 0) >= PAIN_THRESHOLD]
        for phrase, n in key_phrases(pain_texts, exclude=o["topic"], k=3):
            pid = node(f"pain:{phrase}", "pain", phrase, 0)
            nodes[pid]["value"] += n
            G.add_edge(tid, pid, weight=n, kind="has_pain")
        oid = node(f"opp:{o['cluster_id']}", "opportunity", f"{o['scores']['classification']} ({o['scores']['ghostgap']})", o["scores"]["ghostgap"] or 1,
                   opportunity_id=o["_id"], score=o["scores"]["ghostgap"])
        G.add_edge(tid, oid, weight=o["scores"]["ghostgap"] or 1, kind="scored_as")
        p = plan.get(o["_id"])
        rec = o.get("recommendation")
        title = (p or {}).get("title") or (rec or {}).get("title")
        if title:
            cid = node(f"content:{o['cluster_id']}", "content", title, 1, status=(p or {}).get("status", "recommended"),
                       source="planner" if p else (rec or {}).get("generator", "recommendation"))
            G.add_edge(oid, cid, weight=1, kind="recommends")

    pr = nx.pagerank(G, weight="weight") if G.number_of_nodes() else {}
    comm = {}
    if G.number_of_nodes() > 2:
        for i, c in enumerate(nx.community.greedy_modularity_communities(G.to_undirected(), weight="weight")):
            for n in c:
                comm[n] = i
    for n in nodes.values():
        n["pagerank"] = round(pr.get(n["id"], 0), 4)
        n["community"] = comm.get(n["id"])
    shared = [n["label"] for n in nodes.values() if n["type"] == "pain" and G.in_degree(n["id"]) > 1]
    return {"has_data": True, "analysis_id": aid, "nodes": list(nodes.values()),
            "edges": [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)],
            "metrics": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "shared_pain_points": shared,
                        "most_central": sorted(nodes.values(), key=lambda n: -n["pagerank"])[0]["label"] if nodes else None},
            "note": "Content nodes appear when a recommendation exists or you save the opportunity to the planner."}
