"""AGENT 10 - EXPLANATION. Deterministic: turns the computed numbers into an auditable 'why' for every opportunity.
Only statements that follow from measured values are produced; unavailable signals are listed as caveats."""
from app.services import progress

VERDICTS = {
    "ghost_gap": "High audience-content gap: strong audience demand with comparatively little existing content.",
    "saturated": "Saturated: strong audience demand, but substantial existing content already serves it.",
    "niche": "Niche: limited demand and limited existing content.",
    "low_value": "Low value: limited demand and a lot of existing content.",
}


def band(v, lo=40, hi=70):
    return "high" if v >= hi else "moderate" if v >= lo else "low"


def explain(o: dict) -> dict:
    s, facts, caveats = o["scores"], [], []
    facts.append({"label": "Audience volume", "text": f"{o['evidence_count']} related audience comments ({o['share_of_analyzed']}% of those analyzed)"})
    if o["total_engagement"]:
        facts.append({"label": "Engagement", "text": f"{o['total_engagement']} total likes + replies across the cluster"})
    if o["trend"]["available"]:
        g = o["trend"]["growth_percent"]
        facts.append({"label": "Trend", "text": f"{g:+.0f}% change in mentions per {o['trend']['granularity']} (late vs early period)"
                      + (" - low baseline, treat with caution" if o["trend"].get("low_baseline") else "")})
    else:
        caveats.append(o["trend"].get("reason", "Trend unavailable"))
    facts.append({"label": "Audience pain", "text": f"{band(s['pain'])} pain severity ({s['pain']}/100 from embedding-based pain detection)"})
    if len(o["platform_share"]) > 1:
        facts.append({"label": "Cross-platform", "text": ", ".join(f"{p} {v}%" for p, v in o["platform_share"].items())})
    c = o["competition"]
    if c["available"]:
        facts.append({"label": "Competition", "text": f"{band(c['score'])} ({c['score']}/100): ~{c['total_results']:,} YouTube results for '{c['query']}', "
                      f"{round(c['recent_share'] * 100)}% of the top results are from the last 180 days, "
                      f"{round(c['relevance_share'] * 100)}% closely cover this subtopic"
                      + (f"; also measured on {', '.join(c['other_platforms'])}" if c.get("other_platforms") else "")})
    else:
        caveats.append(c.get("reason", "Competition data unavailable") + " - the content gap cannot be confirmed")
    verdict = VERDICTS.get(s["quadrant"]) if s["quadrant"] else "Demand is measured, but whether this is a content gap cannot be confirmed without competition data."
    rec = o.get("recommendation")
    return {"headline": f"{s['classification']} (GhostGap {s['ghostgap']})", "facts": facts, "verdict": verdict, "caveats": caveats,
            "evidence_backed_recommendation": bool(rec)}


def run(state: dict) -> dict:
    for o in state["opportunities"]:
        o["explanation"] = explain(o)
    return {"opportunities": state["opportunities"]}
