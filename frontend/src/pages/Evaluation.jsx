import React, { useCallback, useEffect, useRef, useState } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";
import { CircleAlert, Loader2 } from "lucide-react";
import { errMsg, evalClearLabels, evalCompareEmbedders, evalImportLabels, evalLabels, evalOptions, evalReport, evalSample, evalSaveLabels,
         valDelete, valList, valMetrics, valRefresh, valReport, valTrack } from "../api";

const pct = (v) => (v === null || v === undefined ? "n/a" : `${(v * 100).toFixed(1)}%`);
const f3 = (v) => (v === null || v === undefined ? "n/a" : Number(v).toFixed(3));
const Stat = ({ label, value, hint }) => <div className="lab-stat"><span>{label}</span><strong>{value}</strong>{hint && <small>{hint}</small>}</div>;
const Err = ({ msg }) => (msg ? <div className="ingest-notice-box error"><span>⚠️</span><div><p>{msg}</p></div></div> : null);

function ClassBlock({ title, c }) {
    return (
        <div className="eval-block">
            <h4>{title}</h4>
            <div className="lab-stats">
                <Stat label="Accuracy" value={pct(c.accuracy)} hint={`n = ${c.n}`} />
                <Stat label="Macro F1" value={f3(c.macro_f1)} />
                <Stat label="Majority-class baseline" value={pct(c.majority_baseline_accuracy)} hint={c.majority_class} />
            </div>
            <div className="table-scroll"><table className="data-table">
                <thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead>
                <tbody>{c.per_class.map((r) => <tr key={r.label}><td>{r.label}</td><td>{f3(r.precision)}</td><td>{f3(r.recall)}</td><td>{f3(r.f1)}</td><td>{r.support}</td></tr>)}</tbody>
            </table></div>
            <details><summary>Confusion matrix (rows = your label, columns = prediction)</summary>
                <div className="table-scroll"><table className="data-table confusion">
                    <thead><tr><th></th>{c.confusion.labels.map((l) => <th key={l}>{l}</th>)}</tr></thead>
                    <tbody>{c.confusion.matrix.map((row, i) => {
                        const max = Math.max(...row, 1);
                        return <tr key={i}><th>{c.confusion.labels[i]}</th>{row.map((v, j) => <td key={j} style={{ background: `rgba(15,23,42,${(v / max) * (i === j ? 0.55 : 0.3)})`, color: v / max > 0.5 ? "#fff" : "#0f172a" }}>{v}</td>)}</tr>;
                    })}</tbody>
                </table></div></details>
        </div>
    );
}

function ModelEvaluation() {
    const [opts, setOpts] = useState(null);
    const [labels, setLabels] = useState(null);
    const [sample, setSample] = useState([]);
    const [draft, setDraft] = useState({});
    const [report, setReport] = useState(null);
    const [cmp, setCmp] = useState(null);
    const [busy, setBusy] = useState("");
    const [err, setErr] = useState("");
    const fileRef = useRef();

    const refresh = useCallback(async () => {
        try { setLabels(await evalLabels()); setReport(await evalReport()); } catch (e) { setErr(errMsg(e)); }
    }, []);
    useEffect(() => { evalOptions().then(setOpts).catch((e) => setErr(errMsg(e))); refresh(); }, [refresh]);

    const run = async (key, fn) => { setBusy(key); setErr(""); try { await fn(); } catch (e) { setErr(errMsg(e)); } finally { setBusy(""); } };
    const loadSample = () => run("sample", async () => { const s = await evalSample(20); setSample(s.items); setDraft({}); });
    const save = () => run("save", async () => {
        const items = sample.map((s, i) => ({ text: s.text, ...(draft[i] || {}) })).filter((x) => x.intent && x.sentiment);
        if (!items.length) throw { response: { data: { detail: "Choose an intent and a sentiment for at least one comment." } } };
        await evalSaveLabels(items); setSample([]); await refresh();
    });
    const setField = (i, k, v) => setDraft((d) => ({ ...d, [i]: { ...(d[i] || {}), [k]: v } }));
    const n = labels?.total || 0;
    const cls = report?.classification;

    return (
        <div className="eval-grid">
            <Err msg={err} />
            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">STEP 1 · GROUND TRUTH</span><h3>Label comments by hand</h3>
                    <p>Predictions are hidden while you label, so the labels stay unbiased. Aim for ~100; metrics unlock at {opts?.min_labels || 20}.</p></div>
                    <div className="lab-progress"><strong>{n}</strong> labelled<div className="progress-bar"><div className="progress-fill" style={{ width: `${Math.min(100, n)}%` }} /></div></div></div>
                <div className="btn-row">
                    <button className="demo-btn" onClick={loadSample} disabled={!!busy}>{busy === "sample" ? "Loading…" : "Load 20 comments to label"}</button>
                    <button className="upload-btn" onClick={() => fileRef.current.click()} disabled={!!busy}>Import labelled CSV</button>
                    <input ref={fileRef} type="file" accept=".csv" hidden onChange={(e) => { const f = e.target.files[0]; e.target.value = ""; if (f) run("import", async () => { await evalImportLabels(f); await refresh(); }); }} />
                    {n > 0 && <button className="demo-btn" onClick={() => run("clear", async () => { await evalClearLabels(); await refresh(); })}>Clear all labels</button>}
                    <small className="muted-line">CSV columns: comment, intent, sentiment (optional: topic)</small>
                </div>
                {sample.length > 0 && (
                    <div className="label-list">
                        {sample.map((s, i) => (
                            <div key={i} className="label-row">
                                <p>“{s.text}”</p>
                                <select value={draft[i]?.intent || ""} onChange={(e) => setField(i, "intent", e.target.value)}><option value="">intent…</option>{opts?.intents.map((x) => <option key={x}>{x}</option>)}</select>
                                <select value={draft[i]?.sentiment || ""} onChange={(e) => setField(i, "sentiment", e.target.value)}><option value="">sentiment…</option>{opts?.sentiments.map((x) => <option key={x}>{x}</option>)}</select>
                                <input placeholder="topic (optional)" value={draft[i]?.topic || ""} onChange={(e) => setField(i, "topic", e.target.value)} />
                            </div>))}
                        <button className="ingest-submit-btn" onClick={save} disabled={!!busy}>Save labels</button>
                    </div>)}
            </section>

            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">STEP 2 · CLASSIFIER</span><h3>Intent & sentiment accuracy</h3>
                    <p>{report?.embedder ? `Embedder: ${report.embedder}. ` : ""}The pipeline's embedding-prototype classifier vs your labels.</p></div></div>
                {!cls?.available ? <div className="empty-state compact"><CircleAlert size={22} /><p>{cls?.reason || "Loading…"}</p></div> : (
                    <><ClassBlock title="Intent" c={cls.intent} /><ClassBlock title="Sentiment" c={cls.sentiment} />
                        {report.topic_recovery && <div className="eval-block"><h4>Topic recovery (labelled topics vs clusters)</h4>
                            <div className="lab-stats"><Stat label="Adjusted Rand Index" value={f3(report.topic_recovery.adjusted_rand_index)} hint="1 = perfect, 0 = random" />
                                <Stat label="Normalized mutual info" value={f3(report.topic_recovery.normalized_mutual_info)} />
                                <Stat label="Clusters found" value={report.topic_recovery.predicted_clusters} hint={`${report.topic_recovery.true_topics} true topics`} /></div></div>}</>)}
            </section>

            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">STEP 3 · CLUSTERING</span><h3>Clustering quality (latest analysis)</h3></div></div>
                {report?.clustering ? (
                    <div className="lab-stats">
                        <Stat label="Clusters" value={report.clustering.n_clusters} hint={`${report.clustering.n_points} comments`} />
                        <Stat label="Unclustered (noise)" value={pct(report.clustering.noise_ratio)} />
                        <Stat label="Silhouette (cosine)" value={f3(report.clustering.silhouette_cosine)} hint="higher is better, −1…1" />
                        <Stat label="Davies–Bouldin" value={f3(report.clustering.davies_bouldin)} hint="lower is better" />
                        <Stat label="Cluster sizes" value={report.clustering.cluster_sizes.slice(0, 8).join(", ")} />
                    </div>) : <div className="empty-state compact"><CircleAlert size={22} /><p>Run an analysis first.</p></div>}
            </section>

            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">STEP 4 · ABLATION</span><h3>GhostGap ablation</h3>
                    <p>How much does each component change the ranking? Drop one component (or use it alone) and compare with the full ranking (Kendall τ; 1 = identical order).</p></div></div>
                {report?.ablation?.components ? (
                    <div className="table-scroll"><table className="data-table">
                        <thead><tr><th>Component</th><th>τ without it</th><th>#1 changes?</th><th>New #1</th><th>Top-3 overlap</th><th>τ using only it</th></tr></thead>
                        <tbody>{report.ablation.components.map((c) => c.measured ? (
                            <tr key={c.component}><td><b>{c.component}</b></td><td>{f3(c.drop.kendall_tau)}</td><td>{c.drop.top1_changed ? "yes" : "no"}</td><td>{c.drop.top1_changed ? c.new_top : "—"}</td><td>{c.drop.top3_overlap}/3</td><td>{f3(c.alone.kendall_tau)}</td></tr>
                        ) : <tr key={c.component} className="na"><td><b>{c.component}</b></td><td colSpan={5}>not measured in this analysis (excluded from scoring)</td></tr>)}</tbody>
                    </table></div>) : <div className="empty-state compact"><CircleAlert size={22} /><p>{report?.ablation?.reason || "Run an analysis first."}</p></div>}
            </section>

            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">STEP 5 · EMBEDDERS</span><h3>Semantic model vs lexical baseline</h3>
                    <p>Same comments through each embedder: classification accuracy, clustering quality, and how much the two clusterings agree.</p></div>
                    <button className="demo-btn" disabled={!!busy} onClick={() => run("cmp", async () => setCmp(await evalCompareEmbedders()))}>{busy === "cmp" ? <><Loader2 size={14} className="spin" /> Running…</> : "Compare embedders"}</button></div>
                {cmp && (<>
                    <div className="table-scroll"><table className="data-table">
                        <thead><tr><th>Embedder</th><th>Clusters</th><th>Noise</th><th>Silhouette</th><th>Intent acc.</th><th>Sentiment acc.</th></tr></thead>
                        <tbody>{cmp.embedders.map((e) => e.available === false ? <tr key={e.role} className="na"><td>{e.name}</td><td colSpan={5}>{e.reason}</td></tr> :
                            <tr key={e.role}><td><b>{e.name}</b></td><td>{e.clustering.n_clusters}</td><td>{pct(e.clustering.noise_ratio)}</td><td>{f3(e.clustering.silhouette_cosine)}</td><td>{pct(e.intent_accuracy)}</td><td>{pct(e.sentiment_accuracy)}</td></tr>)}</tbody>
                    </table></div>
                    {cmp.cluster_agreement && <p className="muted-line">Cluster agreement between the two: ARI {f3(cmp.cluster_agreement.adjusted_rand_index)}, NMI {f3(cmp.cluster_agreement.normalized_mutual_info)}.</p>}
                    {cmp.note && <p className="muted-line">{cmp.note}</p>}</>)}
            </section>
        </div>
    );
}

function Validation({ opportunities }) {
    const [items, setItems] = useState([]);
    const [report, setReport] = useState(null);
    const [mature, setMature] = useState(true);
    const [oppId, setOppId] = useState("");
    const [url, setUrl] = useState("");
    const [manual, setManual] = useState({});
    const [err, setErr] = useState("");
    const [busy, setBusy] = useState("");

    const load = useCallback(async () => { try { setItems(await valList()); setReport(await valReport(!mature)); } catch (e) { setErr(errMsg(e)); } }, [mature]);
    useEffect(() => { load(); }, [load]);
    const act = async (key, fn) => { setBusy(key); setErr(""); try { await fn(); await load(); } catch (e) { setErr(errMsg(e)); } finally { setBusy(""); } };

    return (
        <div className="eval-grid">
            <Err msg={err} />
            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">CLOSED LOOP</span><h3>Did GhostGap predict the result?</h3>
                    <p>Track a recommended opportunity once the video is published, then compare real performance (views/day vs the channel's own baseline) with the score predicted <i>at the time</i>. You can also move a planner item to “published”.</p></div></div>
                <div className="btn-row">
                    <select value={oppId} onChange={(e) => setOppId(e.target.value)}><option value="">Select an opportunity to track…</option>
                        {opportunities.map((o) => <option key={o.id} value={o.id}>#{o.rank} {o.topic} (GhostGap {o.scores.ghostgap})</option>)}</select>
                    <input className="grow" placeholder="Published video URL (optional now)" value={url} onChange={(e) => setUrl(e.target.value)} />
                    <button className="ingest-submit-btn" disabled={!oppId || !!busy} onClick={() => act("track", async () => { await valTrack(oppId, url.trim()); setUrl(""); setOppId(""); })}>Track</button>
                </div>
                <div className="table-scroll"><table className="data-table">
                    <thead><tr><th>Topic</th><th>Predicted</th><th>Outcome</th><th>Ratio</th><th>Data</th><th>Actions</th></tr></thead>
                    <tbody>{items.length === 0 && <tr className="na"><td colSpan={6}>Nothing tracked yet.</td></tr>}
                        {items.map((v) => (
                            <tr key={v.id}>
                                <td><b>{v.topic}</b><small className="block">{v.video_url || "no video URL yet"}</small></td>
                                <td>{v.predicted.ghostgap} <small>{v.predicted.classification}</small></td>
                                <td>{v.outcome ? v.outcome.score : "—"}</td>
                                <td>{v.outcome ? `${v.outcome.ratio}×` : "—"}</td>
                                <td>{v.outcome ? `${v.outcome.method}${v.outcome.matured ? "" : " · immature (<14d)"}` : "no outcome yet"}
                                    {v.metrics?.comment_sentiment && <small className="block">comments: {pct(v.metrics.comment_sentiment.positive)} positive, {pct(v.metrics.comment_sentiment.negative)} negative</small>}</td>
                                <td className="actions">
                                    {v.video_url && <button className="mini" disabled={!!busy} onClick={() => act(v.id, () => valRefresh(v.id))}>{busy === v.id ? "…" : "Fetch from YouTube"}</button>}
                                    <span className="manual"><input type="number" placeholder="views" value={manual[v.id]?.views || ""} onChange={(e) => setManual((m) => ({ ...m, [v.id]: { ...m[v.id], views: e.target.value } }))} />
                                        <input type="number" placeholder="baseline" value={manual[v.id]?.base || ""} onChange={(e) => setManual((m) => ({ ...m, [v.id]: { ...m[v.id], base: e.target.value } }))} />
                                        <button className="mini" disabled={!manual[v.id]?.views || !manual[v.id]?.base} onClick={() => act(v.id, () => valMetrics(v.id, Number(manual[v.id].views), Number(manual[v.id].base)))}>Save</button></span>
                                    <button className="mini danger" onClick={() => act(v.id, () => valDelete(v.id))}>✕</button>
                                </td>
                            </tr>))}</tbody>
                </table></div>
                <small className="muted-line">Manual entry: “baseline” = your typical views for comparable videos at the same video age. Outcome = 100·r/(1+r) with r = views ÷ baseline (parity = 50).</small>
            </section>

            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">RESULT</span><h3>Predicted vs actual</h3></div>
                    <label className="ml-check"><input type="checkbox" checked={mature} onChange={(e) => setMature(e.target.checked)} /> only videos ≥ 14 days old</label></div>
                {!report?.available ? <div className="empty-state compact"><CircleAlert size={22} /><p>{report?.reason || "Loading…"}</p></div> : (
                    <>
                        <div className="lab-stats">
                            <Stat label="Tracked videos" value={report.n} />
                            <Stat label="Spearman ρ" value={f3(report.spearman.rho)} hint={`p = ${f3(report.spearman.p_value)}`} />
                            <Stat label="Pearson r" value={f3(report.pearson.r)} />
                            <Stat label="Kendall τ" value={f3(report.kendall_tau)} />
                            <Stat label="GhostGap ≥ 60 beat baseline" value={pct(report.high_score_beat_baseline_rate)} hint={`n = ${report.n_high}`} />
                            <Stat label="GhostGap < 60 beat baseline" value={pct(report.low_score_beat_baseline_rate)} hint={`n = ${report.n_low}`} />
                        </div>
                        <p className={report.reliable ? "verdict" : "caveat"}>{report.interpretation}</p>
                        <div style={{ height: 300 }}><ResponsiveContainer>
                            <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis type="number" dataKey="predicted" name="Predicted GhostGap" domain={[0, 100]} label={{ value: "Predicted GhostGap", position: "insideBottom", offset: -15, fontSize: 12 }} />
                                <YAxis type="number" dataKey="outcome" name="Outcome" domain={[0, 100]} label={{ value: "Outcome score", angle: -90, position: "insideLeft", fontSize: 12 }} />
                                <ReferenceLine y={50} stroke="#94a3b8" strokeDasharray="4 4" label={{ value: "baseline", fontSize: 10 }} />
                                <Tooltip cursor={{ strokeDasharray: "3 3" }} content={({ active, payload }) => active && payload?.length ? <div className="custom-chart-tooltip"><p className="tooltip-rank">{payload[0].payload.topic}</p><p>Predicted {payload[0].payload.predicted} → outcome {payload[0].payload.outcome} ({payload[0].payload.ratio}× baseline)</p></div> : null} />
                                <Scatter data={report.points} fill="#0f172a" /></ScatterChart></ResponsiveContainer></div>
                        <h4>Which components correlate with outcomes? (Spearman)</h4>
                        <div className="comp-bars">{Object.entries(report.per_component_spearman).map(([k, v]) => (
                            <div key={k} className="gg-row"><span className="gg-name">{k}</span>
                                <div className="gg-track diverge"><div className={`gg-fill ${v < 0 ? "neg" : ""}`} style={{ width: `${Math.abs(v || 0) * 50}%`, [v < 0 ? "right" : "left"]: "50%", position: "absolute" }} /></div>
                                <span className="gg-pts">{v === null ? "n/a" : v.toFixed(2)}</span></div>))}</div>
                    </>)}
            </section>
        </div>
    );
}

export default function Evaluation({ opportunities }) {
    const [tab, setTab] = useState("model");
    return (
        <div className="eval-page">
            <div className="mode-toggle big">
                <button className={tab === "model" ? "active" : ""} onClick={() => setTab("model")}>Model evaluation</button>
                <button className={tab === "validation" ? "active" : ""} onClick={() => setTab("validation")}>Closed-loop validation</button>
            </div>
            {tab === "model" ? <ModelEvaluation /> : <Validation opportunities={opportunities} />}
        </div>
    );
}
