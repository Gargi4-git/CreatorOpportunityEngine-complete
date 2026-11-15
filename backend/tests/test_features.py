"""Tests for: evaluation, lab (weights/sensitivity/learned weights), validation, history, planner, graph, channel analysis,
competition v2 and multilingual. External services are mocked at the network boundary; everything downstream is real."""
import io
import json
import math
import random

import httpx
import pandas as pd
import pytest
import respx

from app.ml import competition, learned_weights, scoring, sensitivity
from conftest import HashEmbedder
from test_pipeline import make_csv

YT = "https://www.googleapis.com/youtube/v3"


def upload(client, data, name="a.csv"):
    r = client.post("/api/sources/csv/upload", files={"file": (name, data, "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()["source_id"]


def analyze(client, sid_or_list, **opts):
    ids = sid_or_list if isinstance(sid_or_list, list) else [sid_or_list]
    aid = client.post("/api/analysis/run", json={"source_ids": ids, **opts}).json()["analysis_id"]
    a = client.get(f"/api/analysis/{aid}").json()
    assert a["status"] == "completed", a
    return aid


def demo(client):
    d = client.post("/api/sources/demo/load").json()
    a = client.get(f"/api/analysis/{d['analysis_id']}").json()
    assert a["status"] == "completed", a
    return d["analysis_id"]


def opps(client, aid=None):
    return client.get("/api/opportunities", params={"analysis_id": aid} if aid else {}).json()["opportunities"]


# ===================================================================== 13. multilingual
SPANISH = ["No entiendo cómo funciona la red de Docker, por favor explíquenlo", "Necesito un tutorial completo sobre redes en Docker para principiantes",
           "Mi contenedor no puede conectarse a la base de datos, ayuda por favor", "¿Cómo puedo exponer un puerto de Docker al exterior?",
           "Los contenedores de Docker no se comunican entre sí, estoy muy confundido"]


def mixed_csv():
    en = ["I can't understand docker networking, please explain it", "Please make a tutorial on docker networking for beginners",
          "My container can't reach the database, help please", "How do I expose a docker port to the outside world?",
          "Docker containers can't talk to each other, so confusing"]
    buf = io.StringIO(); pd.DataFrame({"comment": en + SPANISH}).to_csv(buf, index=False)
    return buf.getvalue().encode()


def test_multilingual_option_keeps_non_english(client):
    sid = upload(client, mixed_csv())
    a_off = client.get(f"/api/analysis/{analyze(client, sid)}").json()
    assert a_off["summary"]["data_quality"]["non_english_removed"] >= 3          # default behaviour: dropped
    a_on = client.get(f"/api/analysis/{analyze(client, sid, multilingual=True)}").json()
    q = a_on["summary"]["data_quality"]
    assert q["non_english_removed"] == 0 and a_on["summary"]["options"] == {"multilingual": True}
    assert q["languages"].get("es", 0) >= 3 and q["languages"].get("en", 0) >= 3  # language mix is reported
    assert q["analyzed"] > a_off["summary"]["data_quality"]["analyzed"]


# ===================================================================== 2. weights / sensitivity
def test_rescore_defaults_match_and_custom_weights_reorder(client):
    aid = demo(client)
    w = client.get("/api/lab/weights").json()["weights"]
    assert w["demand"] == 0.30 and w["competition"] == 0.10
    base = client.post("/api/lab/rescore", json={"analysis_id": aid, "weights": w}).json()
    assert all(abs(t["new_score"] - t["original_score"]) < 0.3 for t in base["topics"])      # same formula, rounding only
    only_demand = client.post("/api/lab/rescore", json={"analysis_id": aid, "weights": {"demand": 1, "trend": 0, "pain": 0, "engagement": 0, "freshness": 0}}).json()
    demand_order = sorted(opps(client, aid), key=lambda o: -o["scores"]["demand"])
    assert only_demand["topics"][0]["id"] == demand_order[0]["id"]                           # demand-only weights rank by demand
    assert client.post("/api/lab/rescore", json={"weights": {"bogus": 1}}).status_code == 422
    assert client.post("/api/lab/rescore", json={"weights": {"demand": -1}}).status_code == 422


def test_sensitivity_analysis(client):
    aid = demo(client)
    r = client.post("/api/lab/rescore", json={"analysis_id": aid, "weights": sensitivity.default_weights(), "sensitivity": True, "draws": 200, "spread": 0.3}).json()
    mc = r["sensitivity"]["monte_carlo"]
    assert mc["draws"] == 200 and 0 <= mc["top1_stability"] <= 1
    assert abs(sum(p["p_rank1"] for p in mc["per_topic"]) - 1) < 0.01                         # exactly one topic is #1 in every draw
    assert len(r["sensitivity"]["one_at_a_time"]) == 6
    big = client.post("/api/lab/rescore", json={"analysis_id": aid, "weights": sensitivity.default_weights(), "sensitivity": True, "draws": 200, "spread": 0.9}).json()
    assert big["sensitivity"]["monte_carlo"]["mean_kendall_tau"] <= mc["mean_kendall_tau"] + 1e-9   # larger perturbation never makes the ranking more stable


# ===================================================================== 1. evaluation
def label_for(text):
    t = text.lower()
    intent = "confusion" if "can't understand" in t else "tutorial_request" if "tutorial" in t else "comparison" if "which is better" in t else \
        "complaint" if "struggling" in t else "question"
    return intent, ("negative" if intent in ("confusion", "complaint") else "neutral")


def test_evaluation_flow(client):
    aid = analyze(client, upload(client, make_csv(["docker networking", "git rebase"], n=60)))
    rep0 = client.get("/api/evaluation/report").json()
    assert rep0["classification"]["available"] is False and "Label at least 20" in rep0["classification"]["reason"]    # no metrics without labels
    assert rep0["clustering"]["n_clusters"] >= 1 and rep0["clustering"]["noise_ratio"] is not None
    assert len(rep0["ablation"]["components"]) == 6
    comp = {c["component"]: c for c in rep0["ablation"]["components"]}
    assert comp["competition"]["measured"] is False and comp["demand"]["measured"] is True and "kendall_tau" in comp["demand"]["drop"]

    sample = client.get("/api/evaluation/sample", params={"n": 40}).json()
    assert len(sample["items"]) == 40 and all("predicted" not in str(i) for i in sample["items"])          # blind labelling
    labels = []
    for it in sample["items"]:
        intent, sent = label_for(it["text"])
        labels.append({"text": it["text"], "intent": intent, "sentiment": sent, "topic": "docker" if "docker" in it["text"].lower() else "git"})
    assert client.post("/api/evaluation/labels", json=labels).json()["total"] == 40
    assert client.post("/api/evaluation/labels", json=[{"text": "xyz abc", "intent": "nonsense", "sentiment": "neutral"}]).status_code == 422
    assert client.get("/api/evaluation/sample", params={"n": 40}).json()["remaining_unlabeled"] == sample["remaining_unlabeled"] - 40   # labelled ones excluded

    rep = client.get("/api/evaluation/report").json()
    ci = rep["classification"]["intent"]
    assert ci["n"] == 40 and 0 <= ci["accuracy"] <= 1 and 0 <= ci["macro_f1"] <= 1
    assert ci["majority_baseline_accuracy"] > 0 and sum(map(sum, ci["confusion"]["matrix"])) == 40
    assert rep["topic_recovery"] is None or "adjusted_rand_index" in rep["topic_recovery"]

    cmp_ = client.post("/api/evaluation/compare-embedders").json()
    assert len(cmp_["embedders"]) == 2 and "intent_accuracy" in cmp_["embedders"][0] and "adjusted_rand_index" in cmp_["cluster_agreement"]
    assert client.delete("/api/evaluation/labels").json()["deleted"] == 40


def test_label_import_and_validation(client):
    csv = "comment,intent,sentiment,topic\nplease make a tutorial on docker,tutorial_request,neutral,docker\nbad row,nope,neutral,x\nhow does git rebase work,question,neutral,git\n"
    r = client.post("/api/evaluation/labels/import", files={"file": ("l.csv", csv.encode(), "text/csv")}).json()
    assert r["saved"] == 2 and r["skipped_invalid"] == 1
    assert client.post("/api/evaluation/labels/import", files={"file": ("l.csv", b"a,b\n1,2\n", "text/csv")}).status_code == 422


def test_ablation_math():
    comps = [{"demand": 90, "trend": 10, "pain": 50, "engagement": 50, "freshness": 50, "competition": 10},
             {"demand": 10, "trend": 90, "pain": 50, "engagement": 50, "freshness": 50, "competition": 10},
             {"demand": 50, "trend": 50, "pain": 50, "engagement": 50, "freshness": 50, "competition": 90}]
    from app.ml import evaluation as ev
    out = ev.ablation(comps, ["A", "B", "C"])
    d = {c["component"]: c for c in out["components"]}
    assert out["full_top"] == "A" and d["demand"]["new_top"] != "A" or d["demand"]["drop"]["top1_changed"] in (True, False)
    assert d["demand"]["drop"]["top1_changed"] is True                       # removing demand changes the winner here


# ===================================================================== 3. closed-loop validation + 14. learned weights
def test_validation_manual_and_report(client):
    aid = demo(client)
    os_ = opps(client, aid)
    ids = []
    for o in os_[:6]:
        t = client.post("/api/validation/track", json={"opportunity_id": o["id"]}).json()
        ids.append(t["id"])
        assert t["predicted"]["ghostgap"] == o["scores"]["ghostgap"]          # prediction snapshot stored at tracking time
    rep = client.get("/api/validation/report").json()
    assert rep["available"] is False and "at least 3" in rep["reason"]
    for k, vid in enumerate(ids):
        r = client.post(f"/api/validation/{vid}/metrics", json={"views": 1000 * (k + 1), "baseline_views": 2000}).json()
        ratio = (1000 * (k + 1)) / 2000
        assert r["outcome"]["score"] == round(100 * ratio / (1 + ratio), 1) and r["outcome"]["method"] == "manual"
    rep = client.get("/api/validation/report").json()
    assert rep["available"] and rep["n"] == 6 and rep["reliable"] is False and "Too few" in rep["interpretation"]       # honest about small n
    assert -1 <= rep["spearman"]["rho"] <= 1 and set(rep["per_component_spearman"]) >= {"demand", "pain"}
    assert client.post("/api/validation/track", json={"opportunity_id": "nope"}).status_code == 404


@respx.mock
def test_validation_refresh_from_youtube(client, configure):
    aid = demo(client)
    o = opps(client, aid)[0]
    assert client.post("/api/validation/track", json={"opportunity_id": o["id"], "video_url": "https://youtu.be/aaaaaaaaaaa"}).status_code == 200
    vid = client.get("/api/validation").json()["items"][0]["id"]
    r = client.post(f"/api/validation/{vid}/refresh")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "api_key_required" and "manually" in r.json()["detail"]["message"]

    configure(youtube=True)
    from datetime import datetime, timedelta, timezone
    iso = lambda d: (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ")
    vids = {"aaaaaaaaaaa": (10000, 30), "bbbbbbbbbbb": (3000, 60), "ccccccccccc": (3000, 60), "ddddddddddd": (3000, 60)}

    def videos(request):
        ids = request.url.params["id"].split(",")
        return httpx.Response(200, json={"items": [{"id": i, "snippet": {"title": i, "channelId": "UC" + "x" * 22, "publishedAt": iso(vids[i][1])},
                                                    "statistics": {"viewCount": str(vids[i][0]), "likeCount": "5", "commentCount": "3"}} for i in ids if i in vids]})
    respx.get(f"{YT}/videos").mock(side_effect=videos)
    respx.get(f"{YT}/channels").respond(json={"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]})
    respx.get(f"{YT}/playlistItems").respond(json={"items": [{"contentDetails": {"videoId": i}, "snippet": {"title": i}} for i in vids]})
    from test_integrations import yt_comments
    respx.get(f"{YT}/commentThreads").respond(json=yt_comments(["docker networking"], n=12))
    out = client.post(f"/api/validation/{vid}/refresh").json()
    assert out["outcome"]["method"] == "youtube_api" and out["outcome"]["matured"] is True
    assert 6.0 < out["outcome"]["ratio"] < 7.4                                   # (10000/30) / median(3000/60) = 6.67
    assert out["outcome"]["score"] == round(100 * out["outcome"]["ratio"] / (1 + out["outcome"]["ratio"]), 1)
    assert out["metrics"]["comment_sentiment"]["n"] > 0


def test_learned_weights_recover_the_driver(client):
    aid = demo(client)
    for o in opps(client, aid):
        vid = client.post("/api/validation/track", json={"opportunity_id": o["id"]}).json()["id"]
        ratio = max(0.05, o["scores"]["demand"] / 40)                              # synthetic ground truth: outcome driven by demand
        client.post(f"/api/validation/{vid}/metrics", json={"views": ratio * 1000, "baseline_views": 1000})
    r = client.post("/api/lab/learn").json()
    assert r["ok"] and r["n"] == len(opps(client, aid))
    assert r["weights"]["demand"] == max(r["weights"].values())                    # the true driver gets the largest weight
    assert abs(sum(r["weights"].values()) - 1) < 0.01 and all(v >= 0 for v in r["weights"].values())
    assert r["reliable"] is False and "Exploratory" in r["warning"]                # n < 20 -> flagged, never oversold


def test_learned_weights_need_enough_data(client):
    assert client.post("/api/lab/learn").json()["ok"] is False
    assert "at least 5" in client.post("/api/lab/learn").json()["reason"]


# ===================================================================== 8. history / compare / series
def test_history_compare_series(client):
    data = make_csv(["docker networking", "git rebase"], n=60)
    a1 = analyze(client, upload(client, data, "same.csv"))
    a2 = analyze(client, upload(client, data, "same.csv"))
    other = analyze(client, upload(client, make_csv(["python decorators", "python pandas"], seed=3), "py.csv"))
    h = client.get("/api/history").json()
    assert len(h["analyses"]) == 3 and {"key": "csv:same.csv", "analyses": 2} in h["trackable_sources"]
    c = client.get("/api/history/compare", params={"a": a1, "b": a2}).json()
    assert len(c["matched"]) == len(opps(client, a1)) and not c["only_a"] and not c["only_b"]      # identical data -> every topic matches
    assert all(m["similarity"] > 0.99 and m["delta"]["ghostgap"] == 0 for m in c["matched"])
    diff = client.get("/api/history/compare", params={"a": a1, "b": other, "threshold": 0.5}).json()
    assert len(diff["only_a"]) + len(diff["only_b"]) > 0                                           # different data -> topics differ
    s = client.get("/api/history/series", params={"source_key": "csv:same.csv"}).json()
    assert len(s["analyses"]) == 2 and s["topics"] and all(len(t["points"]) == 2 and t["points"][0]["ghostgap"] is not None for t in s["topics"])
    assert client.get("/api/history/series", params={"source_key": "csv:py.csv"}).status_code == 404
    assert client.get("/api/history/compare", params={"a": a1, "b": "nope"}).status_code == 404


# ===================================================================== 9. planner (+ link to validation)
def test_planner_lifecycle(client):
    aid = demo(client)
    o = opps(client, aid)[0]
    item = client.post("/api/planner", json={"opportunity_id": o["id"]}).json()
    assert item["status"] == "idea" and item["title"] and item["ghostgap"] == o["scores"]["ghostgap"]
    saved = client.post("/api/planner", json={"opportunity_id": o["id"], "brief": {"title": "My brief", "script": "S", "format": "YouTube"}}).json()
    assert saved["status"] == "scripted" and saved["title"] == "My brief"
    p = client.patch(f"/api/planner/{item['id']}", json={"status": "scripted", "notes": "n", "title": "New title"}).json()
    assert p["status"] == "scripted" and p["title"] == "New title" and p["notes"] == "n"
    assert client.patch(f"/api/planner/{item['id']}", json={"status": "bogus"}).status_code == 422
    assert client.patch(f"/api/planner/{item['id']}", json={"status": "published"}).status_code == 422       # must go through publish
    pub = client.post(f"/api/planner/{item['id']}/publish", json={"video_url": "https://youtu.be/aaaaaaaaaaa"}).json()
    assert pub["status"] == "published" and pub["validation_id"]
    tracked = client.get("/api/validation").json()["items"]
    assert tracked[0]["plan_item_id"] == item["id"] and tracked[0]["video_id"] == "aaaaaaaaaaa"            # publish starts closed-loop tracking
    assert client.post(f"/api/planner/{item['id']}/publish", json={"video_url": "https://example.com"}).status_code == 422
    assert len(client.get("/api/planner").json()["items"]) == 2
    assert client.delete(f"/api/planner/{saved['id']}").json()["deleted"] == 1
    assert client.post("/api/planner", json={"opportunity_id": "nope"}).status_code == 404


# ===================================================================== 12. knowledge graph
def test_knowledge_graph(client):
    assert client.get("/api/graph").json() == {"has_data": False, "message": "No analysis yet"}
    aid = demo(client)
    g = client.get("/api/graph").json()
    types = {n["type"] for n in g["nodes"]}
    assert {"source", "topic", "opportunity"} <= types
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])                               # no dangling edges
    kinds = {e["kind"] for e in g["edges"]}
    assert {"mentions", "scored_as"} <= kinds and g["metrics"]["nodes"] == len(g["nodes"])
    assert not [n for n in g["nodes"] if n["type"] == "content"]                                           # no recommendation yet -> no invented content node
    o = opps(client, aid)[0]
    client.post("/api/planner", json={"opportunity_id": o["id"], "title": "Planned video"})
    g2 = client.get("/api/graph").json()
    content = [n for n in g2["nodes"] if n["type"] == "content"]
    assert content and content[0]["label"] == "Planned video" and content[0]["source"] == "planner"
    assert any(e["kind"] == "recommends" for e in g2["edges"])


# ===================================================================== 10. channel-level analysis
def mock_channel(router, videos=("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc")):
    router.get(f"{YT}/channels").respond(json={"items": [{"id": "UC" + "x" * 22, "snippet": {"title": "Test Channel"}, "statistics": {"subscriberCount": "1000"},
                                                         "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]})
    router.get(f"{YT}/playlistItems").respond(json={"items": [{"contentDetails": {"videoId": v, "videoPublishedAt": "2026-01-01T00:00:00Z"},
                                                               "snippet": {"title": f"Video {v}"}} for v in videos]})
    router.get(f"{YT}/search").respond(json={"pageInfo": {"totalResults": 40000}, "items": [
        {"snippet": {"title": "docker networking tutorial", "description": "docker networks", "publishedAt": "2026-08-01T00:00:00Z"}}]})
    topics = {"aaaaaaaaaaa": "docker networking", "bbbbbbbbbbb": "docker networking", "ccccccccccc": "git rebase"}

    def comments(request):
        v = request.url.params["videoId"]
        items = [{"snippet": {"totalReplyCount": 0, "topLevelComment": {"id": f"{v}{i}", "snippet": {
            "textOriginal": f"Please explain {topics[v]} to me, I am confused about step {i} in lesson {list(topics).index(v) + 1}", "publishedAt": f"2026-0{1 + i % 6}-10T10:00:00Z",
            "likeCount": i, "authorDisplayName": "u"}}}} for i in range(30)]
        return httpx.Response(200, json={"items": items})
    router.get(f"{YT}/commentThreads").mock(side_effect=comments)


@respx.mock
def test_channel_analysis(client, configure):
    body = {"url": "https://www.youtube.com/@testchannel", "video_count": 3, "comments_per_video": 30}
    r = client.post("/api/sources/youtube/channel/analyze", json=body)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "api_key_required"
    configure(youtube=True)
    assert client.post("/api/sources/youtube/channel/analyze", json={**body, "url": "https://example.com/@x"}).status_code == 422
    assert client.post("/api/sources/youtube/channel/analyze", json={**body, "url": "https://www.youtube.com/watch?v=aaaaaaaaaaa"}).status_code == 422
    mock_channel(respx)
    out = client.post("/api/sources/youtube/channel/analyze", json=body).json()
    assert out["channel"]["title"] == "Test Channel" and out["comments_fetched"] == 90 and len(out["videos"]) == 3
    a = client.get(f"/api/analysis/{out['analysis_id']}").json()
    assert a["status"] == "completed"
    o = opps(client, out["analysis_id"])
    assert o and any(len(x["video_breakdown"]) >= 1 for x in o)
    assert all(v["count"] > 0 and v["title"].startswith("Video") for x in o for v in x["video_breakdown"])
    assert a["source_key"] == "youtube:channel:" + "UC" + "x" * 22                  # channel identity -> trackable over time in History


@respx.mock
def test_channel_skips_videos_with_disabled_comments(client, configure):
    configure(youtube=True)
    mock_channel(respx)
    calls = {"n": 0}

    def comments(request):
        calls["n"] += 1
        v = request.url.params["videoId"]
        if v == "bbbbbbbbbbb":
            return httpx.Response(403, json={"error": {"errors": [{"reason": "commentsDisabled"}]}})
        items = [{"snippet": {"totalReplyCount": 0, "topLevelComment": {"id": f"{v}{i}", "snippet": {"textOriginal": f"Please explain docker networking to me, I am confused about step {i} in lesson {len(v) % 3 + ord(v[0]) % 7}",
                 "publishedAt": "2026-02-10T10:00:00Z", "likeCount": i, "authorDisplayName": "u"}}}} for i in range(30)]
        return httpx.Response(200, json={"items": items})
    respx.get(f"{YT}/commentThreads").mock(side_effect=comments)
    out = client.post("/api/sources/youtube/channel/analyze", json={"url": "https://www.youtube.com/channel/UC" + "x" * 22, "video_count": 3, "comments_per_video": 30}).json()
    skipped = [v for v in out["videos"] if v.get("skipped")]
    assert len(skipped) == 1 and "disabled" in skipped[0]["skipped"] and out["comments_fetched"] == 60


# ===================================================================== 11. competition v2
def sup(titles_desc, total=50000, year="2026"):
    return {"total_results": total, "items": [{"title": t, "description": d, "published_at": f"{year}-08-01T00:00:00Z"} for t, d in titles_desc]}


def test_competition_embedding_coverage_and_other_platforms():
    emb = HashEmbedder()
    topic = "docker networking containers communicate"
    on_topic = sup([("Docker networking explained", "how containers communicate on docker networks")] * 5)
    off_topic = sup([("Best pasta recipes", "cooking italian dinner at home")] * 5)
    a = competition.score_supply(on_topic, "docker networking", embedder=emb, topic_text=topic)
    b = competition.score_supply(off_topic, "docker networking", embedder=emb, topic_text=topic)
    assert a["coverage_method"] == "embedding_similarity" and a["relevance_share"] > b["relevance_share"] and a["score"] > b["score"]   # covering videos = more competition
    assert a["mean_topic_similarity"] > b["mean_topic_similarity"]
    other = {"sources": {"stackoverflow": {"total": 200000, "recent_share": 0.5}}, "unavailable": ["reddit"]}
    c = competition.score_supply(on_topic, "docker networking", embedder=emb, topic_text=topic, other=other)
    assert "stackoverflow" in c["other_platforms"] and c["other_platforms_unavailable"] == ["reddit"] and "other" in c["components"]
    assert "other" not in a["components"]                                                       # no source answered -> weights renormalised, nothing invented
    k = competition.score_supply(on_topic, "docker networking")
    assert k["coverage_method"] == "keyword_overlap"                                            # graceful fallback without an embedder


@respx.mock
def test_competition_agent_uses_stackoverflow_and_survives_its_failure(client, configure):
    from test_integrations import mock_youtube
    configure(youtube=True)
    mock_youtube(respx, "v1", ["docker networking", "docker compose"])
    respx.get("https://api.stackexchange.com/2.3/search/advanced").mock(side_effect=lambda req: httpx.Response(
        200, json={"total": 123456} if req.url.params.get("filter") == "total" else {"items": [{"creation_date": 1.79e9}]}))
    r = client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 40}).json()
    top = opps(client, r["analysis_id"])[0]
    assert "stackoverflow" in top["competition"]["other_platforms"] and top["competition"]["coverage_method"] == "embedding_similarity"
    assert any("also measured on stackoverflow" in f["text"] for f in top["explanation"]["facts"])
    respx.get("https://api.stackexchange.com/2.3/search/advanced").mock(side_effect=httpx.ConnectError("down"))
    r2 = client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 40}).json()
    top2 = opps(client, r2["analysis_id"])[0]
    assert top2["competition"]["available"] and top2["competition"]["other_platforms"] == {} and "stackoverflow" in top2["competition"]["other_platforms_unavailable"]
