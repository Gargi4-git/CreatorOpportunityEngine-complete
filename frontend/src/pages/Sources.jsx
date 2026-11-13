import React, { useEffect, useState } from "react";
import { MessageSquareText, Database, FileSpreadsheet, Layers } from "lucide-react";
import { getSources } from "../api";
import SourceInput from "../components/SourceInput";
import AnalysisProgress from "../components/AnalysisProgress";
import DatasetBanner from "../components/DatasetBanner";

const Badge = ({ ok, on, off }) => (
    <span className={`source-status-badge ${ok ? "" : "off"}`}><span className={ok ? "status-ping" : "status-off"}></span> {ok ? on : off}</span>
);

export default function Sources({ health, run, startRun, overview }) {
    const [sources, setSources] = useState([]);
    const [stash, setStash] = useState([]);
    const busy = !!run && !["completed", "failed"].includes(run.analysis?.status);
    useEffect(() => { getSources().then(setSources).catch(() => setSources([])); }, [run?.analysis?.status]);

    const by = (t) => sources.filter((s) => s.type === t);
    const stat = (t) => ({ records: by(t).reduce((a, s) => a + s.records, 0), n: by(t).length, last: by(t).find((s) => s.last_analyzed)?.last_analyzed });
    const yt = stat("youtube"), rd = stat("reddit"), csv = stat("csv");
    const fmt = (d) => (d ? new Date(d).toLocaleString() : "never");

    return (
        <div className="sources-page">
            <DatasetBanner overview={overview} />
            <div className="section-heading"><span className="eyebrow">INGESTION CHANNELS</span><h2>Audience Data Pipeline</h2>
                <p>Connect real conversations. A channel shows as connected only when its credentials are actually configured on the server.</p></div>
            <div className="source-grid">
                <div className="source-detail-card">
                    <div className="source-card-header"><div className="source-icon-wrap yt-wrap"><MessageSquareText size={22} /></div>
                        <div><h3>YouTube</h3><Badge ok={health?.youtube.configured} on="API connected" off="YouTube API not connected" /></div></div>
                    <div className="source-stats-row">
                        <div className="source-stat"><span>Records ingested</span><strong>{yt.records}</strong></div>
                        <div className="source-stat"><span>Sources</span><strong>{yt.n}</strong></div>
                        <div className="source-stat"><span>Last analyzed</span><strong>{fmt(yt.last)}</strong></div>
                    </div>
                    <SourceInput kind="youtube" health={health} stash={stash} setStash={setStash} onStarted={startRun} busy={busy} />
                </div>
                <div className="source-detail-card">
                    <div className="source-card-header"><div className="source-icon-wrap rd-wrap"><Database size={22} /></div>
                        <div><h3>Reddit</h3><Badge ok={health?.reddit.configured} on="API connected" off="Reddit integration unavailable" /></div></div>
                    <div className="source-stats-row">
                        <div className="source-stat"><span>Records ingested</span><strong>{rd.records}</strong></div>
                        <div className="source-stat"><span>Sources</span><strong>{rd.n}</strong></div>
                        <div className="source-stat"><span>Last analyzed</span><strong>{fmt(rd.last)}</strong></div>
                    </div>
                    <SourceInput kind="reddit" health={health} stash={stash} setStash={setStash} onStarted={startRun} busy={busy} />
                </div>
                <div className="source-detail-card">
                    <div className="source-card-header"><div className="source-icon-wrap"><FileSpreadsheet size={22} /></div>
                        <div><h3>CSV Upload</h3><Badge ok on="Ready" off="" /></div></div>
                    <div className="source-stats-row">
                        <div className="source-stat"><span>Records</span><strong>{csv.records}</strong></div>
                        <div className="source-stat"><span>Files</span><strong>{csv.n}</strong></div>
                        <div className="source-stat"><span>Last analyzed</span><strong>{fmt(csv.last)}</strong></div>
                    </div>
                    <SourceInput kind="csv" health={health} stash={stash} setStash={setStash} onStarted={startRun} busy={busy} />
                </div>
                <div className="source-detail-card">
                    <div className="source-card-header"><div className="source-icon-wrap"><Layers size={22} /></div>
                        <div><h3>Media (image · audio · video)</h3><Badge ok={health?.gemini.configured} on="Gemini Vision ready" off="Gemini not configured" /></div></div>
                    <p className="source-desc">Whisper: {health?.whisper.message}. Screenshots need Gemini; audio and video are transcribed locally.</p>
                    <SourceInput kind="media" health={health} stash={stash} setStash={setStash} onStarted={startRun} busy={busy} />
                </div>
            </div>

            {run && <AnalysisProgress run={run} />}

            <div className="pipeline-arch-card">
                <div className="section-heading"><span className="eyebrow">INTELLIGENCE STACK</span><h2>What actually runs</h2>
                    <p>Classical ML and statistics where computation is deterministic; embeddings for semantics; Gemini only for interpretation and generation.</p></div>
                <div className="arch-flow">
                    {[["Ingestion & Cleaning", "Spam, duplicate, near-duplicate, language and timestamp handling (rules + embedding similarity)."],
                      ["Multimodal Fusion", "Screenshots (Gemini Vision), audio (Whisper) and video frames are converted to text and embedded alongside comments."],
                      ["Embeddings & Clustering", "all-MiniLM-L6-v2 (384-d) vectors, HDBSCAN density clustering, FAISS index."],
                      ["Statistical Scoring", "Demand, trend (Pandas), freshness, pain/intent (embedding prototypes) and GhostGap are computed in Python."],
                      ["Gemini + RAG", "Topic naming and recommendations from retrieved evidence; unverifiable citations are rejected."]]
                        .map(([h, p], i) => <div key={h} className="arch-step"><div className="step-num">0{i + 1}</div><h4>{h}</h4><p>{p}</p></div>)}
                </div>
            </div>
        </div>
    );
}
