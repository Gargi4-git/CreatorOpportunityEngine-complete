import React, { useCallback, useEffect, useRef, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { ArrowDown, ArrowUp, Minus, CircleAlert, Loader2 } from "lucide-react";
import { errMsg, labLearn, labRescore, labWeights } from "../api";

const LABELS = { demand: "Demand", trend: "Trend", pain: "Pain", engagement: "Engagement", freshness: "Freshness", competition: "Competition (penalty)" };
const Delta = ({ d }) => (d > 0 ? <span className="up"><ArrowUp size={13} />{d}</span> : d < 0 ? <span className="down"><ArrowDown size={13} />{-d}</span> : <span className="same"><Minus size={13} /></span>);

export default function Lab({ overview, onNavigate }) {
    const [defaults, setDefaults] = useState(null);
    const [w, setW] = useState(null);
    const [res, setRes] = useState(null);
    const [spread, setSpread] = useState(0.3);
    const [sens, setSens] = useState(null);
    const [learn, setLearn] = useState(null);
    const [err, setErr] = useState("");
    const [busy, setBusy] = useState("");
    const timer = useRef();

    useEffect(() => { labWeights().then((d) => { setDefaults(d.weights); setW(d.weights); }).catch((e) => setErr(errMsg(e))); }, []);
    const rescore = useCallback((weights) => {
        clearTimeout(timer.current);
        timer.current = setTimeout(async () => { try { setRes(await labRescore(weights)); setErr(""); } catch (e) { setErr(errMsg(e)); } }, 200);
    }, []);
    useEffect(() => { if (w && overview?.has_data) { rescore(w); setSens(null); } }, [w, overview?.has_data, rescore]);

    if (!overview?.has_data) {
        return <div className="empty-state"><CircleAlert size={36} /><h3>No analysis yet</h3><p>The lab re-ranks the opportunities of your latest analysis.</p>
            <button className="refresh-button" onClick={() => onNavigate("creator-studio")}>Analyze Audience</button></div>;
    }
    if (!w) return <div className="loading-state"><Loader2 className="spin" size={26} /></div>;

    const changed = Object.keys(w).some((k) => Math.abs(w[k] - defaults[k]) > 0.0001);
    const runSens = async () => { setBusy("sens"); try { setSens((await labRescore(w, true, spread)).sensitivity); } catch (e) { setErr(errMsg(e)); } finally { setBusy(""); } };
    const runLearn = async () => { setBusy("learn"); try { setLearn(await labLearn()); } catch (e) { setErr(errMsg(e)); } finally { setBusy(""); } };
    const mc = sens?.monte_carlo;

    return (
        <div className="lab-page">
            {err && <div className="ingest-notice-box error"><span>⚠️</span><div><p>{err}</p></div></div>}
            <div className="lab-split">
                <section className="lab-card">
                    <div className="lab-card-head"><div><span className="eyebrow">WEIGHTS</span><h3>GhostGap formula</h3>
                        <p>Weights need not sum to 1: scores are re-normalised over the achievable range.</p></div>
                        <button className="demo-btn" disabled={!changed} onClick={() => setW(defaults)}>Reset</button></div>
                    {Object.keys(LABELS).map((k) => (
                        <div key={k} className="slider-row">
                            <label>{LABELS[k]}</label>
                            <input type="range" min="0" max="1" step="0.01" value={w[k]} onChange={(e) => setW({ ...w, [k]: Number(e.target.value) })} />
                            <span className={Math.abs(w[k] - defaults[k]) > 0.0001 ? "changed" : ""}>{w[k].toFixed(2)}<small> (default {defaults[k].toFixed(2)})</small></span>
                        </div>))}
                    <div className="sens-controls">
                        <label>Perturbation ±{Math.round(spread * 100)}%</label>
                        <input type="range" min="0.1" max="0.6" step="0.05" value={spread} onChange={(e) => setSpread(Number(e.target.value))} />
                        <button className="ingest-submit-btn" onClick={runSens} disabled={!!busy}>{busy === "sens" ? "Simulating…" : "Run sensitivity analysis"}</button>
                    </div>
                </section>

                <section className="lab-card">
                    <div className="lab-card-head"><div><span className="eyebrow">LIVE RANKING</span><h3>Re-ranked opportunities</h3></div></div>
                    <div className="table-scroll"><table className="data-table">
                        <thead><tr><th>#</th><th>Topic</th><th>Score</th><th>was</th><th>Δ rank</th></tr></thead>
                        <tbody>{res?.topics.map((t) => (
                            <tr key={t.id}><td><b>{t.new_rank}</b></td><td>{t.topic}</td>
                                <td><div className="score-cell"><div style={{ width: `${t.new_score ?? 0}%` }} /><span>{t.new_score ?? "n/a"}</span></div></td>
                                <td>{t.original_rank} <small>({t.original_score})</small></td><td><Delta d={t.rank_change} /></td></tr>))}</tbody>
                    </table></div>
                </section>
            </div>

            {mc && (
                <section className="lab-card">
                    <div className="lab-card-head"><div><span className="eyebrow">SENSITIVITY</span><h3>How stable is the #1 opportunity?</h3>
                        <p>{mc.draws} random re-weightings, each weight scaled by a random factor within ±{Math.round(mc.spread * 100)}%.</p></div></div>
                    <div className="lab-stats">
                        <div className={`lab-stat big ${mc.top1_stability >= 0.8 ? "good" : mc.top1_stability >= 0.5 ? "mid" : "bad"}`}><span>“{mc.baseline_top_topic}” stays #1</span><strong>{Math.round(mc.top1_stability * 100)}%</strong><small>of draws</small></div>
                        <div className="lab-stat"><span>Mean rank agreement (Kendall τ)</span><strong>{mc.mean_kendall_tau ?? "n/a"}</strong></div>
                    </div>
                    <div style={{ height: Math.max(220, mc.per_topic.length * 30) }}><ResponsiveContainer>
                        <BarChart layout="vertical" data={[...mc.per_topic].sort((a, b) => b.p_rank1 - a.p_rank1).map((p) => ({ ...p, pct: Math.round(p.p_rank1 * 100) }))} margin={{ left: 20, right: 30 }}>
                            <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
                            <YAxis type="category" dataKey="topic" width={190} tick={{ fontSize: 11 }} interval={0} tickFormatter={(t) => (t.length > 28 ? `${t.slice(0, 27)}…` : t)} /><Tooltip />
                            <Bar dataKey="pct" name="Probability of being #1" fill="#0f172a" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div>
                    <h4>Change one weight at a time (±50%)</h4>
                    <div className="table-scroll"><table className="data-table"><thead><tr><th>Weight</th><th>Halved → #1</th><th>Raised 50% → #1</th></tr></thead>
                        <tbody>{sens.one_at_a_time.map((r) => <tr key={r.weight}><td><b>{LABELS[r.weight]}</b></td>
                            <td className={r.down.flipped ? "flip" : ""}>{r.down.flipped ? `changes to “${r.down.top_topic}”` : "unchanged"}</td>
                            <td className={r.up.flipped ? "flip" : ""}>{r.up.flipped ? `changes to “${r.up.top_topic}”` : "unchanged"}</td></tr>)}</tbody></table></div>
                </section>)}

            <section className="lab-card">
                <div className="lab-card-head"><div><span className="eyebrow">LEARNED WEIGHTS</span><h3>Fit the weights from real outcomes</h3>
                    <p>Non-negative ridge regression of tracked-video outcomes on the component scores recorded at prediction time (Evaluation → Closed-loop validation).</p></div>
                    <button className="demo-btn" onClick={runLearn} disabled={!!busy}>{busy === "learn" ? "Fitting…" : "Fit from validation data"}</button></div>
                {learn && !learn.ok && <div className="empty-state compact"><CircleAlert size={22} /><p>{learn.reason}</p></div>}
                {learn?.ok && (<>
                    {learn.warning && <p className="caveat">⚠ {learn.warning}</p>}
                    <div className="lab-stats">
                        <div className="lab-stat"><span>Videos used</span><strong>{learn.n}</strong></div>
                        <div className="lab-stat"><span>R² in-sample</span><strong>{learn.r2_in_sample}</strong></div>
                        <div className="lab-stat"><span>R² leave-one-out</span><strong>{learn.r2_leave_one_out ?? "n/a"}</strong><small>honest out-of-sample estimate</small></div>
                        <div className="lab-stat"><span>Spearman: default score vs outcome</span><strong>{learn.spearman_default_vs_outcome ?? "n/a"}</strong></div>
                    </div>
                    <div className="comp-bars">{Object.keys(LABELS).map((k) => (
                        <div key={k} className="gg-row"><span className="gg-name">{k}</span>
                            <div className="gg-track"><div className="gg-fill" style={{ width: `${learn.weights[k] * 100}%` }} /></div>
                            <span className="gg-pts">{learn.weights[k].toFixed(2)} <small>vs {learn.default_weights[k].toFixed(2)}</small></span></div>))}</div>
                    <button className="demo-btn" onClick={() => setW(learn.weights)}>Preview these weights in the ranking</button>
                </>)}
            </section>
        </div>
    );
}
