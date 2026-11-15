import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { ArrowDown, ArrowUp, CircleAlert } from "lucide-react";
import { errMsg, historyCompare, historyList, historySeries } from "../api";

const COLORS = ["#0f172a", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444"];
const D = ({ v, suffix = "" }) => (v === null || v === undefined ? <span className="same">n/a</span> : v > 0 ? <span className="up"><ArrowUp size={12} />{v}{suffix}</span> : v < 0 ? <span className="down"><ArrowDown size={12} />{-v}{suffix}</span> : <span className="same">0</span>);
const when = (d) => (d ? new Date(d).toLocaleString() : "—");

export default function History({ onNavigate }) {
    const [data, setData] = useState(null);
    const [picked, setPicked] = useState([]);
    const [cmp, setCmp] = useState(null);
    const [threshold, setThreshold] = useState(0.5);
    const [series, setSeries] = useState(null);
    const [err, setErr] = useState("");

    useEffect(() => { historyList().then(setData).catch((e) => setErr(errMsg(e))); }, []);
    const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p.slice(-1), id]));   // keep the last two picks
    const compare = async () => { setErr(""); setCmp(null); try { setCmp(await historyCompare(picked[0], picked[1], threshold)); } catch (e) { setErr(errMsg(e)); } };
    const loadSeries = async (key) => { setErr(""); setSeries(null); try { setSeries(await historySeries(key)); } catch (e) { setErr(errMsg(e)); } };

    if (!data) return err ? <div className="ingest-notice-box error"><p>{err}</p></div> : null;
    if (!data.analyses.length) return <div className="empty-state"><CircleAlert size={36} /><h3>No analyses yet</h3><p>Every analysis you run is kept here.</p>
        <button className="refresh-button" onClick={() => onNavigate("creator-studio")}>Analyze Audience</button></div>;

    const chart = series ? series.analyses.map((a, i) => ({ date: new Date(a.date).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }), ...Object.fromEntries(series.topics.map((t) => [t.topic, t.points[i]?.ghostgap])) })) : [];

    return (
        <div className="history-page">
            {err && <div className="ingest-notice-box error"><span>⚠️</span><div><p>{err}</p></div></div>}
            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">ALL ANALYSES</span><h3>Pick two to compare</h3></div>
                    <div className="btn-row"><label className="ml-check">match threshold {threshold.toFixed(2)}
                        <input type="range" min="0.2" max="0.9" step="0.05" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} /></label>
                        <button className="ingest-submit-btn" disabled={picked.length !== 2} onClick={compare}>Compare selected</button></div></div>
                <div className="table-scroll"><table className="data-table">
                    <thead><tr><th></th><th>Source</th><th>When</th><th>Comments</th><th>Topics</th><th>Avg GhostGap</th><th>Top topic</th></tr></thead>
                    <tbody>{data.analyses.map((a) => (
                        <tr key={a.id} className={a.status !== "completed" ? "na" : ""}>
                            <td><input type="checkbox" disabled={a.status !== "completed"} checked={picked.includes(a.id)} onChange={() => toggle(a.id)} /></td>
                            <td><b>{a.label}</b>{a.options?.multilingual && <small className="block">multilingual</small>}</td><td>{when(a.completed_at || a.created_at)}</td>
                            <td>{a.comments ?? "—"}</td><td>{a.topics ?? "—"}</td><td>{a.avg_ghostgap ?? "—"}</td>
                            <td>{a.status === "completed" ? `${a.top_topic} (${a.top_score})` : a.status}</td></tr>))}</tbody>
                </table></div>
            </section>

            {cmp && (
                <section className="lab-card">
                    <div className="lab-card-head"><div><span className="eyebrow">COMPARISON</span><h3>{cmp.a.label} <small>vs</small> {cmp.b.label}</h3><p>{cmp.note}</p></div></div>
                    <div className="cmp-cols">
                        {["a", "b"].map((k) => (
                            <div key={k} className="cmp-col"><h4>{k === "a" ? "A" : "B"} · {when(cmp[k].completed_at)}</h4>
                                <ul><li><b>{cmp[k].summary.audience_comments}</b> comments</li><li><b>{cmp[k].summary.clustering.clusters}</b> topics</li>
                                    <li>avg GhostGap <b>{cmp[k].summary.avg_opportunity_score ?? "n/a"}</b></li><li>avg trend <b>{cmp[k].summary.avg_trend ?? "n/a"}</b></li>
                                    <li>platforms: {Object.entries(cmp[k].summary.platforms).map(([p, n]) => `${p} ${n}`).join(", ")}</li></ul></div>))}
                    </div>
                    <h4>Matched topics ({cmp.matched.length})</h4>
                    <div className="table-scroll"><table className="data-table">
                        <thead><tr><th>Topic (B)</th><th>Match</th><th>GhostGap A → B</th><th>Demand Δ</th><th>Trend Δ</th><th>Pain Δ</th><th>Comments Δ</th></tr></thead>
                        <tbody>{cmp.matched.length === 0 && <tr className="na"><td colSpan={7}>No topics matched at this threshold — lower it to match more loosely.</td></tr>}
                            {cmp.matched.map((m, i) => <tr key={i}><td><b>{m.b.topic}</b><small className="block">A: {m.a.topic}</small></td><td>{m.similarity}</td>
                                <td>{m.a.ghostgap} → {m.b.ghostgap} <D v={m.delta.ghostgap} /></td><td><D v={m.delta.demand} /></td><td><D v={m.delta.trend} /></td><td><D v={m.delta.pain} /></td><td><D v={m.delta.evidence} /></td></tr>)}</tbody>
                    </table></div>
                    <div className="cmp-cols">
                        <div className="cmp-col"><h4>Only in A ({cmp.only_a.length})</h4><ul>{cmp.only_a.map((t) => <li key={t.id}>{t.topic} <small>GG {t.ghostgap}</small></li>)}</ul></div>
                        <div className="cmp-col"><h4>Only in B ({cmp.only_b.length})</h4><ul>{cmp.only_b.map((t) => <li key={t.id}>{t.topic} <small>GG {t.ghostgap}</small></li>)}</ul></div>
                    </div>
                </section>)}

            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">OVER TIME</span><h3>Same source, repeated analyses</h3>
                    <p>Analyses of the same channel, subreddit or file are linked. Pick one to see how its top topics moved.</p></div></div>
                {data.trackable_sources.length === 0 ? <div className="empty-state compact"><CircleAlert size={22} /><p>Run a second analysis of the same channel / file to unlock this view.</p></div> : (
                    <div className="btn-row">{data.trackable_sources.map((s) => <button key={s.key} className="demo-btn" onClick={() => loadSeries(s.key)}>{s.key} ({s.analyses} analyses)</button>)}</div>)}
                {series && (
                    <div style={{ height: 320 }}><ResponsiveContainer>
                        <LineChart data={chart} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis domain={[0, 100]} tick={{ fontSize: 11 }} /><Tooltip /><Legend />
                            {series.topics.map((t, i) => <Line key={t.topic} type="monotone" dataKey={t.topic} stroke={COLORS[i % COLORS.length]} strokeWidth={2} connectNulls />)}
                        </LineChart></ResponsiveContainer></div>)}
            </section>
        </div>
    );
}
