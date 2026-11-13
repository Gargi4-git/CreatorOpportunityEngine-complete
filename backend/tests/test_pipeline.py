import io
import random

import pandas as pd

from app.ml import scoring


def make_csv(subjects, n=60, seed=1, days=100):
    rnd = random.Random(seed)
    templates = ["I can't understand {s} at all, please explain it", "Please make a full tutorial on {s} for beginners",
                 "How do I get started with {s} in production?", "Struggling with {s}, nothing works for me",
                 "Which is better for {s}, option {x} or option {y}?"]
    rows = []
    for i in range(n):
        s = rnd.choice(subjects)
        t = rnd.choice(templates).format(s=s, x=rnd.choice("ABCDEFG"), y=rnd.choice("HIJKLMN"))
        # later days get more mentions of subject 0 (growth)
        day = int(days * (rnd.random() ** (0.6 if s == subjects[0] else 1.4)))
        rows.append({"comment": f"{t} #{i} v{rnd.randint(1, 999)}", "timestamp": f"2026-06-{1 + day % 28:02d}" if False
                     else (pd.Timestamp("2026-06-01") + pd.Timedelta(days=day)).strftime("%Y-%m-%d"),
                     "likes": rnd.randint(0, 30), "replies": rnd.randint(0, 5), "platform": rnd.choice(["YouTube", "Reddit"])})
    # include junk to exercise cleaning
    rows += [{"comment": "", "timestamp": "", "likes": 0, "replies": 0, "platform": "YouTube"},
             {"comment": "Subscribe to my channel http://a.com http://b.com", "timestamp": "", "likes": 1, "replies": 0, "platform": "YouTube"}]
    buf = io.StringIO(); pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue().encode()


def run(client, data, name="x.csv"):
    up = client.post("/api/sources/csv/upload", files={"file": (name, data, "text/csv")})
    assert up.status_code == 200, up.text
    rep = up.json()
    r = client.post("/api/analysis/run", json={"source_ids": [rep["source_id"]]})
    aid = r.json()["analysis_id"]
    a = client.get(f"/api/analysis/{aid}").json()  # BackgroundTasks run before TestClient returns
    return rep, a


def test_health_is_honest(client):
    h = client.get("/api/health").json()
    assert h["gemini"]["configured"] is False or "configured" in h["gemini"]["message"].lower()
    assert "mongodb" in h


def test_csv_report_and_pipeline(client):
    rep, a = run(client, make_csv(["docker networking", "kubernetes ingress"]))
    assert rep["column_mapping"]["text"] == "comment" and rep["invalid_records"] == 1
    assert a["status"] == "completed", a
    dq = a["summary"]["data_quality"]
    assert dq["empty_removed"] == 0 and dq["spam_removed"] == 1       # empty row was already counted as invalid at upload
    steps = {s["key"]: s["status"] for s in a["steps"]}
    assert steps["competition"] == "skipped" and steps["recommend"] == "skipped"   # never faked
    opps = client.get("/api/opportunities").json()["opportunities"]
    assert opps and all(o["scores"]["competition"] is None for o in opps)
    o = client.get(f"/api/opportunities/{opps[0]['id']}").json()
    assert o["recommendation"] is None and o["representative_comments"]
    assert "competition" in o["unavailable_components"]


def test_different_csv_gives_different_results(client):
    _, a1 = run(client, make_csv(["python decorators", "python pandas"], seed=3), "py.csv")
    t1 = {o["topic"] for o in client.get("/api/opportunities", params={"analysis_id": a1["analysis_id"]}).json()["opportunities"]}
    _, a2 = run(client, make_csv(["kubernetes ingress", "kubernetes helm"], seed=4), "k8s.csv")
    t2 = {o["topic"] for o in client.get("/api/opportunities", params={"analysis_id": a2["analysis_id"]}).json()["opportunities"]}
    assert t1 and t2 and t1.isdisjoint(t2)
    assert any("python" in t.lower() for t in t1) and any("kubernetes" in t.lower() or "helm" in t.lower() or "ingress" in t.lower() for t in t2)


def test_no_timestamps_means_trend_unavailable(client):
    df = pd.read_csv(io.BytesIO(make_csv(["docker networking", "git rebase"], seed=5))).drop(columns=["timestamp", "likes", "replies"])
    buf = io.StringIO(); df.to_csv(buf, index=False)
    _, a = run(client, buf.getvalue().encode())
    assert a["status"] == "completed"
    for o in client.get("/api/opportunities").json()["opportunities"]:
        assert o["scores"]["trend"] is None and o["trend"]["available"] is False
        assert "trend" in o["unavailable_components"] and "engagement" in o["unavailable_components"]


def test_bad_uploads(client):
    assert client.post("/api/sources/csv/upload", files={"file": ("a.exe", b"x", "application/octet-stream")}).status_code == 400
    assert client.post("/api/sources/csv/upload", files={"file": ("a.csv", b"", "text/csv")}).status_code == 422
    assert client.post("/api/sources/csv/upload", files={"file": ("a.csv", b"a,b\n1,2\n", "text/csv")}).status_code == 422


def test_ghostgap_math():
    full = scoring.ghostgap({"demand": 100, "trend": 100, "pain": 100, "engagement": 100, "freshness": 100, "competition": 0})
    assert full["score"] == 100 and full["classification"] == "Critical Opportunity"
    worst = scoring.ghostgap({"demand": 0, "trend": 0, "pain": 0, "engagement": 0, "freshness": 0, "competition": 100})
    assert worst["score"] == 0
    partial = scoring.ghostgap({"demand": 80, "trend": None, "pain": 60, "engagement": None, "freshness": None, "competition": None})
    assert partial["score"] == 72.0 and set(partial["unavailable"]) == {"trend", "engagement", "freshness", "competition"}
