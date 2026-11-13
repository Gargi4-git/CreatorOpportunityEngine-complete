import io
import json
import subprocess

import httpx
import pandas as pd
import pytest
import respx

from app.services import gemini_service, whisper_service
from conftest import FakeGemini, FakeWhisper
from test_pipeline import make_csv

YT = "https://www.googleapis.com/youtube/v3"


def yt_comments(subjects, n=40, base="c"):
    import random
    rnd = random.Random(7)
    tpl = ["I can't understand {s}, please explain it", "Please make a tutorial on {s}", "How do I use {s} in production?",
           "Struggling with {s}, nothing works", "Which is better for {s}, option {x} or {y}?"]
    items = []
    for i in range(n):
        s = rnd.choice(subjects)
        t = rnd.choice(tpl).format(s=s, x=rnd.choice("ABCDEFG"), y=rnd.choice("HIJKLMN")) + f" #{i}"
        day = 1 + (i * 3) % 28
        items.append({"snippet": {"totalReplyCount": 0, "topLevelComment": {"id": f"{base}{i}", "snippet": {
            "textOriginal": t, "publishedAt": f"2026-{1 + (i % 9):02d}-{day:02d}T10:00:00Z", "likeCount": i % 17, "authorDisplayName": "u"}}}})
    return {"items": items}


def mock_youtube(router, vid, subjects, comments_resp=None):
    router.get(f"{YT}/videos").respond(json={"items": [{"snippet": {"title": f"Video {vid}", "channelTitle": "Ch", "publishedAt": "2026-01-01T00:00:00Z"},
                                                        "statistics": {"viewCount": "10", "commentCount": "40"}}]})
    router.get(f"{YT}/commentThreads").respond(json=comments_resp or yt_comments(subjects, base=vid))
    router.get(f"{YT}/search").respond(json={"pageInfo": {"totalResults": 50000}, "items": [
        {"snippet": {"title": "docker networking tutorial", "publishedAt": "2026-08-01T00:00:00Z"}},
        {"snippet": {"title": "something else", "publishedAt": "2021-01-01T00:00:00Z"}}]})


def run_source(client, sid):
    aid = client.post("/api/analysis/run", json={"source_ids": [sid]}).json()["analysis_id"]
    return client.get(f"/api/analysis/{aid}").json()


# ------------------------------------------------------------ YouTube
@respx.mock
def test_youtube_end_to_end_with_competition_and_gemini(client, configure):
    configure(youtube=True, gemini=True)
    mock_youtube(respx, "v1", ["docker networking", "docker compose"])
    r = client.post("/api/sources/youtube/analyze", json={"url": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "comment_limit": 40})
    assert r.status_code == 200, r.text
    a = client.get(f"/api/analysis/{r.json()['analysis_id']}").json()
    assert a["status"] == "completed", a
    steps = {s["key"]: s["status"] for s in a["steps"]}
    assert steps["competition"] == "done" and steps["recommend"] == "done"
    top = client.get("/api/opportunities").json()["opportunities"][0]
    assert top["scores"]["competition"] is not None and top["scores"]["quadrant"] in ("ghost_gap", "saturated", "niche", "low_value")
    assert top["recommendation_status"] == "generated" and top["recommendation"]["evidence"]        # RAG evidence resolved
    assert top["topic_label_source"] == "gemini" and top["explanation"]["verdict"]
    assert a["summary"]["gemini_used"] is True


@respx.mock
def test_different_youtube_urls_give_different_results(client, configure):
    configure(youtube=True)
    mock_youtube(respx, "v1", ["python decorators", "python pandas"])
    s1 = client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 40}).json()
    mock_youtube(respx, "v2", ["kubernetes ingress", "kubernetes helm"])
    s2 = client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/bbbbbbbbbbb", "comment_limit": 40}).json()
    t = lambda s: {o["topic"] for o in client.get("/api/opportunities", params={"analysis_id": s["analysis_id"]}).json()["opportunities"]}
    assert t(s1) and t(s2) and t(s1).isdisjoint(t(s2))


def test_youtube_errors_are_human_readable(client, configure):
    r = client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 50})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "api_key_required"       # no key -> no pretending
    configure(youtube=True)
    assert client.post("/api/sources/youtube/analyze", json={"url": "https://example.com/x", "comment_limit": 50}).status_code == 422
    assert "channel URL" in client.post("/api/sources/youtube/analyze", json={"url": "https://youtube.com/@x", "comment_limit": 50}).json()["detail"]
    with respx.mock:
        respx.get(f"{YT}/videos").respond(json={"items": [{"snippet": {"title": "t"}, "statistics": {}}]})
        respx.get(f"{YT}/commentThreads").respond(403, json={"error": {"errors": [{"reason": "commentsDisabled"}]}})
        assert "disabled" in client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 50}).json()["detail"]
        respx.get(f"{YT}/commentThreads").respond(403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}})
        assert "quota" in client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 50}).json()["detail"]
        respx.get(f"{YT}/videos").respond(json={"items": []})
        assert "not found" in client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 50}).json()["detail"]


@respx.mock
def test_competition_quota_failure_marks_unavailable_not_fake(client, configure):
    configure(youtube=True)
    mock_youtube(respx, "v1", ["docker networking", "docker compose"])
    respx.get(f"{YT}/search").respond(403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}})
    r = client.post("/api/sources/youtube/analyze", json={"url": "https://youtu.be/aaaaaaaaaaa", "comment_limit": 40}).json()
    a = client.get(f"/api/analysis/{r['analysis_id']}").json()
    assert a["status"] == "completed" and any("quota" in w for w in a["summary"]["warnings"])
    assert all(o["scores"]["competition"] is None for o in client.get("/api/opportunities").json()["opportunities"])


# ------------------------------------------------------------ Gemini / RAG guard
def test_recommendation_with_unverifiable_citations_is_rejected(client, configure):
    configure(gemini=True)
    gemini_service.set_client(FakeGemini(evidence_ids=[98, 99]))
    sid = client.post("/api/sources/csv/upload", files={"file": ("a.csv", make_csv(["docker networking", "git rebase"]), "text/csv")}).json()["source_id"]
    a = run_source(client, sid)
    assert a["status"] == "completed"
    top = client.get("/api/opportunities").json()["opportunities"][0]
    assert top["recommendation"] is None and top["recommendation_status"].startswith("rejected")


def test_gemini_garbage_is_a_controlled_error(configure):
    configure(gemini=True)
    bad = FakeGemini(); bad.models.generate_content = lambda **k: type("R", (), {"text": "not json"})()
    gemini_service.set_client(bad)
    with pytest.raises(gemini_service.GeminiError, match="invalid response"):
        gemini_service.analyze_text("hello world")


# ------------------------------------------------------------ Reddit
@respx.mock
def test_reddit(client, configure):
    r = client.post("/api/sources/reddit/analyze", json={"target": "r/Python", "limit": 20})
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]["message"]
    configure(reddit=True)
    assert client.post("/api/sources/reddit/analyze", json={"target": "not a target!", "limit": 20}).status_code == 422
    respx.post("https://www.reddit.com/api/v1/access_token").respond(json={"access_token": "t"})
    posts = [{"kind": "t3", "data": {"id": f"p{i}", "title": f"How do I deploy ml model number {i}", "selftext": "please help", "created_utc": 1.78e9 + i * 86400,
                                      "score": i, "num_comments": 3, "author": "a", "subreddit": "Python", "permalink": f"/r/Python/comments/p{i}/x/"}} for i in range(12)]
    respx.get("https://oauth.reddit.com/r/Python/hot").respond(json={"data": {"children": posts}})
    comment = {"kind": "t1", "data": {"id": "c1", "body": "I struggle with deployment too", "created_utc": 1.78e9, "score": 5, "author": "b", "permalink": "/r/Python/comments/p0/x/c1"}}
    respx.get(url__regex=r"https://oauth.reddit.com/r/Python/comments/.*").respond(json=[{}, {"data": {"children": [comment]}}])
    out = client.post("/api/sources/reddit/analyze", json={"target": "r/Python", "limit": 20}).json()
    assert out["records_fetched"] >= 12
    assert client.get(f"/api/analysis/{out['analysis_id']}").json()["status"] in ("completed", "failed")


# ------------------------------------------------------------ Multimodal fusion (acceptance test 3)
def test_text_image_audio_fuse_into_one_topic(client, configure):
    configure(gemini=True)
    gemini_service.set_client(FakeGemini(image_topic="ML model deployment"))
    whisper_service.set_model(FakeWhisper("I don't know how to deploy my ML model. I tried three tutorials."))
    texts = ["How do I deploy my ML model?", "Struggling to deploy my machine learning model to production", "ML model deployment is confusing, please explain",
             "Can you show how to deploy a trained ML model as an API?", "I can't deploy my model, nothing works"] + \
            ["Docker compose networking is confusing", "Please explain docker bridge networks", "Docker containers can't reach each other, help",
             "How do docker networks work?", "Docker network drivers explained please"]
    df = pd.DataFrame({"comment": texts}); buf = io.StringIO(); df.to_csv(buf, index=False)
    s_txt = client.post("/api/sources/csv/upload", files={"file": ("t.csv", buf.getvalue().encode(), "text/csv")}).json()["source_id"]
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    img = client.post("/api/sources/image/analyze", files={"file": ("err.png", png, "image/png")})
    assert img.status_code == 200 and img.json()["result"]["topic"] == "ML model deployment"
    aud = client.post("/api/sources/audio/analyze", files={"file": ("a.wav", b"RIFF" + b"0" * 100, "audio/wav")}).json()
    src = client.get(f"/api/sources/{aud['source_id']}").json()
    assert src["status"] == "ready" and "deploy" in src["meta"]["result"]["transcript"]          # transcript is returned to the user
    ids = [s_txt, img.json()["source_id"], aud["source_id"]]
    aid = client.post("/api/analysis/run", json={"source_ids": ids}).json()["analysis_id"]
    a = client.get(f"/api/analysis/{aid}").json()
    assert a["status"] == "completed", a
    assert {"text", "image", "audio"} <= set(a["summary"]["modalities"])
    opps = client.get("/api/opportunities").json()["opportunities"]
    fused = [o for o in opps if len(o["modality_mix"]) >= 2]
    assert fused and any("deploy" in o["topic"].lower() or "model" in o["topic"].lower() for o in fused)   # one unified topic, not three


def test_media_validation(client, configure):
    f = lambda n, b: {"file": (n, b, "application/octet-stream")}
    assert client.post("/api/sources/image/analyze", files=f("x.gif", b"GIF89a")).status_code == 400
    assert client.post("/api/sources/image/analyze", files=f("x.png", b"MZnotapng" * 10)).status_code == 400
    assert client.post("/api/sources/image/analyze", files=f("x.png", b"\x89PNG" + b"0" * 50)).status_code == 503   # Gemini not configured
    assert "not configured" in client.post("/api/sources/image/analyze", files=f("x.png", b"\x89PNG" + b"0" * 50)).json()["detail"]
    assert client.post("/api/sources/audio/analyze", files=f("x.ogg", b"OggS")).status_code == 400
    assert client.post("/api/sources/audio/analyze", files=f("x.wav", b"RIFF" + b"0" * 50)).status_code == 503     # whisper missing/unmocked


def test_video_pipeline_transcript_and_frames(client, configure, tmp_path):
    configure(gemini=True)
    whisper_service.set_model(FakeWhisper("Today we look at docker networking and why containers cannot reach each other."))
    mp4 = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10", "-f", "lavfi", "-i", "sine=duration=2",
                    "-shortest", "-pix_fmt", "yuv420p", str(mp4)], check=True, capture_output=True)
    r = client.post("/api/sources/video/analyze", files={"file": ("v.mp4", mp4.read_bytes(), "video/mp4")}).json()
    s = client.get(f"/api/sources/{r['source_id']}").json()
    assert s["status"] == "ready", s
    res = s["meta"]["result"]
    assert "docker networking" in res["transcript"] and res["visual"]["visual_topics"]          # transcript + real extracted frames sent to vision
    recs = list(__import__("app.db.mongodb", fromlist=["get_db"]).get_db().audience_records.find({"source_ref": r["source_id"]}))
    assert {x["modality"] for x in recs} == {"video"} and len(recs) >= 2


# ------------------------------------------------------------ demo / analytics / studio / search
def test_demo_dataset_runs_same_pipeline_and_feeds_analytics(client, configure):
    assert client.get("/api/analytics/overview").json() == {"has_data": False, "message": "No analysis yet"}
    d = client.post("/api/sources/demo/load").json()
    assert d["dataset_label"] == "demo"
    a = client.get(f"/api/analysis/{d['analysis_id']}").json()
    assert a["status"] == "completed" and [s["status"] for s in a["steps"]].count("done") >= 8
    o = client.get("/api/analytics/overview").json()
    assert o["has_data"] and o["dataset_labels"] == ["demo"] and o["summary"]["audience_comments"] > 100
    assert o["topic_distribution"] and o["trend_over_time"]["available"] and sum(b["count"] for b in o["score_distribution"]) == len(o["demand_by_topic"])
    assert o["competition_vs_demand"]["available"] is False and "unavailable" in o["competition_vs_demand"]["reason"]
    assert {p["name"] for p in o["platform_distribution"]} <= {"youtube", "reddit"}
    src = client.get("/api/sources").json()["sources"][0]
    assert src["dataset_label"] == "demo" and src["last_analyzed"]


def test_creator_studio_generate_grounded_in_opportunity(client, configure):
    sid = client.post("/api/sources/csv/upload", files={"file": ("a.csv", make_csv(["docker networking", "git rebase"]), "text/csv")}).json()["source_id"]
    run_source(client, sid)
    opp = client.get("/api/opportunities").json()["opportunities"][0]
    no_key = client.post("/api/creator-studio/generate", json={"opportunity_id": opp["id"], "format": "blog"})
    assert no_key.status_code == 503 and "not configured" in no_key.json()["detail"]                 # no canned content
    configure(gemini=True)
    r = client.post("/api/creator-studio/generate", json={"opportunity_id": opp["id"], "format": "linkedin"}).json()
    assert r["brief"]["script"] and r["video_generation"]["available"] is False
    assert [e["id"] for e in r["brief"]["evidence"]] == [1]       # id 99 does not exist -> dropped, id 1 verified
    assert client.post("/api/creator-studio/generate", json={"opportunity_id": "nope", "format": "blog"}).status_code == 404


def test_semantic_search_and_graph_is_langgraph(client):
    sid = client.post("/api/sources/csv/upload", files={"file": ("a.csv", make_csv(["docker networking", "git rebase"]), "text/csv")}).json()["source_id"]
    run_source(client, sid)
    res = client.get("/api/search", params={"q": "docker networking help"}).json()
    assert res["results"] and res["backend"] in ("faiss", "numpy-bruteforce")
    from app.agents.orchestrator import build_graph
    g = build_graph().get_graph()
    assert {"ingestion", "multimodal", "topic", "sentiment", "demand", "trend", "competition", "ghostgap", "recommendation", "explanation", "persist"} <= set(g.nodes)
