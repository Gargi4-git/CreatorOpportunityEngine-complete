import React, { useEffect, useMemo, useState } from "react";
import { errMsg, generateBrief, planCreate } from "./api";
import SourceInput from "./components/SourceInput";
import AnalysisProgress from "./components/AnalysisProgress";
import { num, oppTitle } from "./format";
import "./CreatorStudio.css";

const SOURCES = [["youtube", "YouTube", "yt"], ["reddit", "Reddit", "rd"], ["csv", "CSV", "csv"], ["media", "Upload Media", "csv"]];
const FORMATS = [["youtube", "YouTube", "Long-form"], ["shorts", "Shorts", "Under 60s"], ["reel", "Instagram Reel", "Vertical"], ["blog", "Blog", "Article"], ["linkedin", "LinkedIn Post", "Professional"]];

export default function CreatorStudio({ health, run, startRun, opportunities, studioOppId, setStudioOppId }) {
    const [source, setSource] = useState("youtube");
    const [stash, setStash] = useState([]);
    const [format, setFormat] = useState("youtube");
    const [gen, setGen] = useState({ loading: false, error: null, data: null });
    const [copied, setCopied] = useState(false);
    const [saved, setSaved] = useState(null);

    const running = !!run && !["completed", "failed"].includes(run.analysis?.status);
    const opp = useMemo(() => opportunities.find((o) => o.id === studioOppId) || opportunities[0], [opportunities, studioOppId]);
    useEffect(() => { setGen({ loading: false, error: null, data: null }); setSaved(null); }, [opp?.id]);
    const saveToPlanner = async () => { try { await planCreate(opp.id, { brief: gen.data.brief, format: gen.data.format }); setSaved("ok"); } catch (e) { setSaved(errMsg(e)); } };

    const generate = async () => {
        setGen({ loading: true, error: null, data: null });
        try { setGen({ loading: false, error: null, data: await generateBrief(opp.id, format) }); }
        catch (e) { setGen({ loading: false, error: errMsg(e), data: null }); }
    };
    const copy = () => {
        const b = gen.data.brief;
        navigator.clipboard.writeText(`${b.title}\n\nHOOK: ${b.hook}\n\nOUTLINE:\n${b.outline.map((x, i) => `${i + 1}. ${x}`).join("\n")}\n\nSCRIPT:\n${b.script}\n\nCTA: ${b.cta}`);
        setCopied(true); setTimeout(() => setCopied(false), 1500);
    };

    return (
        <div className="creator-studio">
            <div className="creator-studio-header">
                <div><div className="eyebrow">CREATOR WORKSPACE</div><h1>Creator Studio</h1>
                    <p>Analyze real audience conversations, find the opportunity with the strongest evidence, and generate a grounded content brief.</p></div>
                <div className="studio-status"><span className={`status-dot ${health?.gemini.configured ? "" : "down"}`}></span>
                    {health?.gemini.configured ? "Gemini configured" : "Gemini not configured"}</div>
            </div>

            <section className="studio-ingest-card">
                <div className="ingest-header">
                    <div><div className="section-label">ANALYZE YOUR AUDIENCE</div><h2>Source</h2>
                        <p>Pick where the audience data comes from. Every number you see afterwards is computed from it.</p></div>
                    <div className="source-pill-group">
                        {SOURCES.map(([id, label, dot]) => (
                            <button key={id} type="button" className={source === id ? "source-pill active" : "source-pill"} onClick={() => setSource(id)}>
                                <span className={`source-pill-dot ${dot}`}></span> {label}
                            </button>))}
                    </div>
                </div>
                <SourceInput kind={source} health={health} stash={stash} setStash={setStash} onStarted={startRun} busy={running} />
            </section>

            {run && <AnalysisProgress run={run} />}

            {opp ? (
                <>
                    <section className="studio-opportunity">
                        <div className="section-label">TOP AUDIENCE OPPORTUNITY
                            {opportunities.length > 1 && (
                                <select className="opp-select" value={opp.id} onChange={(e) => setStudioOppId(e.target.value)}>
                                    {opportunities.map((o) => <option key={o.id} value={o.id}>#{o.rank} {o.topic} ({num(o.scores.ghostgap)})</option>)}
                                </select>)}
                        </div>
                        <div className="opportunity-content">
                            <div>
                                <h2>{oppTitle(opp)}</h2>
                                <p>{opp.recommendation?.reason || opp.audience_need || opp.explanation?.verdict}</p>
                                <div className="studio-scores">
                                    {[["GhostGap", opp.scores.ghostgap], ["Demand", opp.scores.demand], ["Trend", opp.scores.trend], ["Pain", opp.scores.pain], ["Competition", opp.scores.competition]]
                                        .map(([k, v]) => <div key={k} className={v === null ? "na" : ""}><span>{k}</span><strong>{num(v, 0)}</strong></div>)}
                                    <div><span>Evidence</span><strong>{opp.evidence_count}</strong></div>
                                </div>
                                <ul className="why-list">{opp.explanation?.facts.map((f) => <li key={f.label}><strong>{f.label}:</strong> {f.text}</li>)}</ul>
                                {opp.explanation?.caveats.map((c, i) => <p key={i} className="caveat">⚠ {c}</p>)}
                            </div>
                        </div>
                    </section>

                    <section className="studio-section">
                        <div className="section-heading"><div><div className="section-label">CONTENT GENERATOR</div><h2>Generate Content Brief</h2>
                            <p>Written by Gemini from the evidence behind this opportunity — not from a template.</p></div></div>
                        <div className="video-format-options" style={{ flexWrap: "wrap" }}>
                            {FORMATS.map(([id, label, sub]) => (
                                <button key={id} type="button" className={format === id ? "format-option active" : "format-option"} onClick={() => setFormat(id)}>
                                    <span><strong>{label}</strong><small>{sub}</small></span></button>))}
                        </div>
                        <button className="primary-studio-button" style={{ marginTop: 16 }} onClick={generate} disabled={gen.loading}>
                            {gen.loading ? "Generating…" : "✦ Generate Content Brief"}</button>
                        <p className="muted-line">Video generation unavailable — Creator Studio produces the script and brief, not an MP4.</p>
                    </section>

                    <section className="studio-result-section">
                        <div className="section-label">CONTENT BRIEF</div>
                        <div className="result-card">
                            {gen.loading ? <div className="loading-state"><div className="loading-spinner"></div><h3>Generating from audience evidence…</h3></div>
                            : gen.error ? <div className="ingest-notice-box error"><span>⚠️</span><div><strong>Could not generate</strong><p>{gen.error}</p></div></div>
                            : gen.data ? (() => { const b = gen.data.brief; return (
                                <div className="result-content brief">
                                    <div className="result-header"><div><span className="result-label">{gen.data.format.toUpperCase()} · {b.length}</span><h3>{b.title}</h3></div>
                                        <div className="result-actions"><button className="copy-result-button" onClick={copy}>{copied ? "✓ Copied" : "Copy Brief"}</button>
                                            <button className="copy-result-button" onClick={saveToPlanner} disabled={saved === "ok"}>{saved === "ok" ? "✓ Saved to planner" : "Save to planner"}</button></div></div>
                                    <h4>Hook</h4><p>{b.hook}</p>
                                    <h4>Target audience</h4><p>{b.target_audience}</p>
                                    <h4>Outline</h4><ol>{b.outline.map((x, i) => <li key={i}>{x}</li>)}</ol>
                                    <h4>Script</h4><p style={{ whiteSpace: "pre-wrap" }}>{b.script}</p>
                                    <h4>CTA</h4><p>{b.cta}</p>
                                    {b.evidence.length > 0 && (<><h4>Audience evidence used</h4>
                                        <ul className="evidence-list">{b.evidence.map((e) => <li key={e.id}>“{e.text}” <small>{e.platform}</small></li>)}</ul></>)}
                                </div>); })()
                            : <div className="empty-result"><div className="empty-icon">✦</div><h3>Your content brief will appear here</h3>
                                <p>Choose a format and click “Generate Content Brief”.</p></div>}
                        </div>
                    </section>
                </>
            ) : (
                !run && <section className="studio-opportunity"><div className="section-label">TOP AUDIENCE OPPORTUNITY</div>
                    <div className="opportunity-content"><div><h2>No analysis yet</h2><p>Choose a source above and click Analyze Audience. Opportunities and briefs appear here once real data has been processed.</p></div></div></section>
            )}
        </div>
    );
}
