import React, { useEffect, useRef, useState } from "react";
import { FlaskConical, Upload, Image as ImageIcon, Mic, Film, KeyRound } from "lucide-react";
import { analyzeReddit, analyzeYoutube, analyzeYoutubeChannel, errCode, errMsg, getSource, loadDemo, runAnalysis, uploadAudio, uploadCsv, uploadImage, uploadVideo } from "../api";

const LIMITS = [100, 250, 500, 1000];

/**
 * One input panel for every source type. Everything it shows comes from the API:
 * - YouTube/Reddit fetch real data (or show an explicit "API key required" state)
 * - CSV/media uploads are validated by the backend and listed in the stash; the user then analyzes the selected inputs together
 */
export default function SourceInput({ kind, health, stash, setStash, onStarted, busy }) {
    const [url, setUrl] = useState("");
    const [limit, setLimit] = useState(250);
    const [working, setWorking] = useState(false);
    const [mode, setMode] = useState("video");          // YouTube: single video | whole channel
    const [videoCount, setVideoCount] = useState(5);
    const [perVideo, setPerVideo] = useState(100);
    const [multilingual, setMultilingual] = useState(false);
    const [notice, setNotice] = useState(null);
    const fileRefs = { csv: useRef(), image: useRef(), audio: useRef(), video: useRef() };

    const fail = (e) => setNotice({ type: "error", title: errCode(e) === "api_key_required" ? "Demo mode / API key required" : "Something went wrong", text: errMsg(e) });

    // poll audio/video sources that are still being transcribed
    useEffect(() => {
        const pending = stash.filter((s) => s.status === "processing");
        if (!pending.length) return undefined;
        const t = setInterval(async () => {
            for (const p of pending) {
                try {
                    const s = await getSource(p.id);
                    if (s.status !== "processing") setStash((st) => st.map((x) => (x.id === p.id ? { ...x, status: s.status, error: s.error, result: s.meta?.result } : x)));
                } catch { /* keep polling */ }
            }
        }, 1500);
        return () => clearInterval(t);
    }, [stash, setStash]);

    const guard = async (fn) => { setWorking(true); setNotice(null); try { await fn(); } catch (e) { fail(e); } finally { setWorking(false); } };

    const startYoutube = () => guard(async () => {
        if (mode === "channel") {
            const c = await analyzeYoutubeChannel(url.trim(), videoCount, perVideo, multilingual);
            onStarted(c.analysis_id, `Channel: ${c.channel.title}`);
            const skipped = c.videos.filter((v) => v.skipped).length;
            setNotice({ type: "success", title: `Fetched ${c.comments_fetched} comments from ${c.videos.length - skipped} videos`,
                text: c.channel.title + (skipped ? ` — ${skipped} video(s) skipped (comments disabled)` : "") });
            return;
        }
        const r = await analyzeYoutube(url.trim(), limit, multilingual);
        onStarted(r.analysis_id, `YouTube: ${r.video.title}`);
        setNotice({ type: "success", title: `Fetched ${r.comments_fetched} real comments`, text: `${r.video.title} — ${r.video.channel}` });
    });
    const startReddit = () => guard(async () => {
        const r = await analyzeReddit(url.trim(), limit, multilingual);
        onStarted(r.analysis_id, `Reddit: ${r.subreddit}`);
        setNotice({ type: "success", title: `Fetched ${r.records_fetched} posts/comments`, text: `r/${r.subreddit}` });
    });
    const startDemo = () => guard(async () => {
        const r = await loadDemo(multilingual);
        onStarted(r.analysis_id, "Demo Dataset (synthetic)");
    });
    const addFile = (type, fn) => async (e) => {
        const f = e.target.files?.[0]; e.target.value = "";
        if (!f) return;
        guard(async () => {
            const r = await fn(f);
            const item = { id: r.source_id, type, label: f.name, selected: true, status: r.status || "ready", report: type === "csv" ? r : null, result: r.result };
            setStash((st) => [...st, item]);
        });
    };
    const analyzeStash = () => guard(async () => {
        const ids = stash.filter((s) => s.selected && s.status === "ready").map((s) => s.id);
        const r = await runAnalysis(ids, multilingual);
        onStarted(r.analysis_id, ids.length > 1 ? `${ids.length} fused inputs` : stash.find((s) => s.id === ids[0])?.label);
    });

    const keyMissing = (kind === "youtube" && !health?.youtube.configured) || (kind === "reddit" && !health?.reddit.configured);
    const disabled = working || busy;
    const sel = stash.filter((s) => s.selected && s.status === "ready");

    return (
        <div className="source-input">
            {(kind === "youtube" || kind === "reddit") && (
                <>
                    {keyMissing && (
                        <div className="ingest-notice-box error">
                            <KeyRound size={16} />
                            <div><strong>Demo mode / API key required</strong>
                                <p>{kind === "youtube" ? "YouTube API not connected — set YOUTUBE_API_KEY in the backend .env." : "Reddit integration unavailable — set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT."} No real data can be fetched until then.</p></div>
                        </div>
                    )}
                    {kind === "youtube" && (
                        <div className="mode-toggle">
                            <button type="button" className={mode === "video" ? "active" : ""} onClick={() => setMode("video")}>Single video</button>
                            <button type="button" className={mode === "channel" ? "active" : ""} onClick={() => setMode("channel")}>Whole channel (last N videos)</button>
                        </div>
                    )}
                    <div className="ingest-form-row">
                        <div className="ingest-input-wrap">
                            <span className="ingest-input-icon">🔗</span>
                            <input type="text" className="ingest-url-input" disabled={disabled}
                                   placeholder={kind === "youtube" ? (mode === "channel" ? "https://www.youtube.com/@channelname" : "https://www.youtube.com/watch?v=...") : "r/MachineLearning or a Reddit post URL"}
                                   value={url} onChange={(e) => setUrl(e.target.value)} />
                        </div>
                        {kind === "youtube" && mode === "channel" ? (
                            <>
                                <div className="ingest-select-wrap"><label className="ingest-select-label">Videos:</label>
                                    <select className="ingest-limit-select" value={videoCount} disabled={disabled} onChange={(e) => setVideoCount(Number(e.target.value))}>
                                        {[3, 5, 10, 15, 25].map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
                                <div className="ingest-select-wrap"><label className="ingest-select-label">Comments/video:</label>
                                    <select className="ingest-limit-select" value={perVideo} disabled={disabled} onChange={(e) => setPerVideo(Number(e.target.value))}>
                                        {[50, 100, 250].map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
                            </>
                        ) : (
                            <div className="ingest-select-wrap">
                                <label className="ingest-select-label">{kind === "youtube" ? "Comments:" : "Posts/comments:"}</label>
                                <select className="ingest-limit-select" value={limit} disabled={disabled} onChange={(e) => setLimit(Number(e.target.value))}>
                                    {LIMITS.slice(0, kind === "reddit" ? 3 : 4).map((n) => <option key={n} value={n}>{n}</option>)}
                                </select>
                            </div>
                        )}
                        <button type="button" className="ingest-submit-btn" disabled={disabled || keyMissing || !url.trim()} onClick={kind === "youtube" ? startYoutube : startReddit}>
                            {working ? "Fetching…" : kind === "youtube" ? "✦ Analyze Audience" : "✦ Analyze"}
                        </button>
                    </div>
                </>
            )}

            {(kind === "csv" || kind === "media") && (
                <div className="upload-row">
                    {kind === "csv" && (
                        <button className="upload-btn" disabled={disabled} onClick={() => fileRefs.csv.current.click()}><Upload size={15} /> Upload CSV</button>
                    )}
                    {kind === "media" && (<>
                        <button className="upload-btn" disabled={disabled} onClick={() => fileRefs.image.current.click()}><ImageIcon size={15} /> Upload Image</button>
                        <button className="upload-btn" disabled={disabled} onClick={() => fileRefs.audio.current.click()}><Mic size={15} /> Upload Audio</button>
                        <button className="upload-btn" disabled={disabled} onClick={() => fileRefs.video.current.click()}><Film size={15} /> Upload Video</button>
                    </>)}
                    <input ref={fileRefs.csv} type="file" accept=".csv" hidden onChange={addFile("csv", uploadCsv)} />
                    <input ref={fileRefs.image} type="file" accept=".png,.jpg,.jpeg,.webp" hidden onChange={addFile("image", uploadImage)} />
                    <input ref={fileRefs.audio} type="file" accept=".mp3,.wav,.m4a" hidden onChange={addFile("audio", uploadAudio)} />
                    <input ref={fileRefs.video} type="file" accept=".mp4,.mov" hidden onChange={addFile("video", uploadVideo)} />
                    <small>{kind === "csv" ? "Columns like comment/text, timestamp, likes, replies, platform are detected automatically." :
                        "PNG/JPG/WEBP screenshots (Gemini Vision), MP3/WAV/M4A (Whisper), MP4/MOV (audio + frames). Upload several and analyze them together."}</small>
                </div>
            )}

            {working && (kind === "csv" || kind === "media") && <div className="muted-line">Uploading and validating…</div>}

            {(kind === "csv" || kind === "media") && stash.length > 0 && (
                <div className="stash">
                    {stash.map((s) => (
                        <div key={s.id} className={`stash-item ${s.status}`}>
                            <label>
                                <input type="checkbox" checked={!!s.selected} disabled={s.status !== "ready"}
                                       onChange={() => setStash((st) => st.map((x) => (x.id === s.id ? { ...x, selected: !x.selected } : x)))} />
                                <strong>{s.label}</strong> <em>{s.type}</em>
                                {s.status === "processing" && <span className="chip-processing">transcribing…</span>}
                                {s.status === "failed" && <span className="chip-failed">{s.error}</span>}
                            </label>
                            {s.report && (
                                <div className="csv-report">
                                    <span>{s.report.rows_detected} rows</span><span>{s.report.columns_detected.length} columns ({s.report.columns_detected.join(", ")})</span>
                                    <span>{s.report.valid_records} valid</span><span>{s.report.invalid_records} invalid</span>
                                    <span>text column: <b>{s.report.column_mapping.text}</b></span>
                                </div>
                            )}
                            {s.type === "image" && s.result && (
                                <div className="media-result"><div><b>Topic</b> {s.result.topic}</div><div><b>Intent</b> {s.result.intent}</div>
                                    <div><b>Pain</b> {s.result.pain_point}</div><div><b>Sentiment</b> {s.result.sentiment}</div>
                                    {s.result.visible_text && <div className="wide"><b>Visible text</b> {s.result.visible_text}</div>}</div>
                            )}
                            {(s.type === "audio" || s.type === "video") && s.result && (
                                <div className="media-result">
                                    <div className="wide"><b>Transcript</b> {s.result.transcript}</div>
                                    {s.result.analysis && <div className="wide"><b>Key topic</b> {s.result.analysis.topic} · {s.result.analysis.intent}</div>}
                                    {s.result.visual && <div className="wide"><b>Visual topics</b> {s.result.visual.visual_topics.join(", ")}</div>}
                                    {(s.result.visual_unavailable || s.result.analysis_unavailable) && <div className="wide muted">{s.result.visual_unavailable || s.result.analysis_unavailable}</div>}
                                </div>
                            )}
                        </div>
                    ))}
                    <button className="ingest-submit-btn" disabled={disabled || !sel.length} onClick={analyzeStash}>
                        ✦ {kind === "csv" ? "Analyze Dataset" : "Analyze"} {sel.length > 1 ? `(${sel.length} inputs fused)` : ""}
                    </button>
                </div>
            )}

            {notice && (
                <div className={`ingest-notice-box ${notice.type}`}><span>{notice.type === "success" ? "✓" : "⚠️"}</span>
                    <div><strong>{notice.title}</strong><p>{notice.text}</p></div></div>
            )}

            <label className="ml-check">
                <input type="checkbox" checked={multilingual} onChange={(e) => setMultilingual(e.target.checked)} />
                Include non-English comments <small>(uses a multilingual embedding model; otherwise non-English comments are removed)</small>
            </label>
            <div className="demo-row">
                <button className="demo-btn" disabled={disabled} onClick={startDemo}><FlaskConical size={14} /> Load Demo Dataset</button>
                <small>Clearly labelled synthetic sample — runs through the same pipeline; never presented as live data.</small>
            </div>
        </div>
    );
}
