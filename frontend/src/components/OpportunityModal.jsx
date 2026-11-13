import React from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Sparkles, X, Target, HelpCircle, Lightbulb, Video, TrendingUp, Swords, MessageSquareQuote, ListChecks } from "lucide-react";
import GhostGapBreakdown from "./GhostGapBreakdown";
import { num, oppTitle } from "../format";

const Section = ({ icon: Icon, title, children }) => (
    <div className="detail-section"><div className="detail-header"><Icon size={16} /><h4>{title}</h4></div>{children}</div>
);

export default function OpportunityModal({ opportunity: o, onClose, onGenerate }) {
    if (!o) return null;
    const s = o.scores, rec = o.recommendation, ex = o.explanation, c = o.competition, tr = o.trend;
    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div>
                        <div className="modal-eyebrow-row">
                            <span className="modal-label">OPPORTUNITY BRIEF</span>
                            <span className="modal-rank-pill">Rank #{o.rank}</span>
                            <span className="modal-platform-pill">{Object.keys(o.platform_share).join(" + ")}</span>
                        </div>
                        <h2>{oppTitle(o)}</h2>
                        <small className="topic-sub">Topic: {o.topic} <em>({o.topic_label_source})</em></small>
                    </div>
                    <button className="close-button" onClick={onClose} aria-label="Close modal"><X size={18} /></button>
                </div>

                <div className="modal-score">
                    <div><span>GhostGap Score</span><strong>{num(s.ghostgap)} / 100</strong></div>
                    <div><span>Classification</span><strong>{s.classification}</strong></div>
                    <div><span>Evidence</span><strong>{o.evidence_count} comments ({o.total_engagement.toLocaleString()} engagement)</strong></div>
                </div>

                <Section icon={HelpCircle} title="AUDIENCE NEED">
                    <p>{o.audience_need || "No AI-written description available (Gemini not used for this topic). Topic label is keyword-derived."}</p>
                    <small className="topic-sub">Cluster cohesion confidence: {num(o.unified_confidence, 2)} · Modalities: {Object.entries(o.modality_mix).map(([m, n]) => `${m} ${n}`).join(", ")}</small>
                </Section>

                {ex && (
                    <Section icon={ListChecks} title="WHY THIS MATTERS">
                        <ul className="why-list">{ex.facts.map((f) => <li key={f.label}><strong>{f.label}:</strong> {f.text}</li>)}</ul>
                        <p className="verdict">{ex.verdict}</p>
                        {ex.caveats.map((cv, i) => <p key={i} className="caveat">⚠ {cv}</p>)}
                    </Section>
                )}

                <Section icon={Target} title="GHOSTGAP BREAKDOWN">
                    <GhostGapBreakdown breakdown={o.ghostgap_breakdown} score={s.ghostgap} classification={s.classification} />
                </Section>

                <Section icon={TrendingUp} title="TREND">
                    {tr.available ? (
                        <>
                            <p>{tr.growth_percent >= 0 ? "+" : ""}{tr.growth_percent}% change in mentions per {tr.granularity} (early mean {tr.early_mean} → late mean {tr.late_mean}). Trend score {s.trend}.</p>
                            <div style={{ height: 160 }}>
                                <ResponsiveContainer>
                                    <LineChart data={tr.series} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                        <XAxis dataKey="period" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 10 }} /><Tooltip />
                                        <Line type="monotone" dataKey="mentions" stroke="#0f172a" strokeWidth={2} dot={{ r: 2 }} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </>
                    ) : <p className="caveat">{tr.reason}</p>}
                </Section>

                <Section icon={Swords} title="COMPETITION ANALYSIS">
                    {c.available ? (
                        <p>Score {c.score}/100 for query “{c.query}”: about {c.total_results.toLocaleString()} YouTube results (estimate); {Math.round(c.recent_share * 100)}% of the top {c.sampled} are
                            from the last 180 days; {Math.round(c.relevance_share * 100)}% have closely matching titles.</p>
                    ) : <p className="caveat">Competition data unavailable. {c.reason}</p>}
                </Section>

                <Section icon={MessageSquareQuote} title="REPRESENTATIVE AUDIENCE COMMENTS">
                    <ul className="evidence-list">
                        {o.representative_comments.map((cm, i) => (
                            <li key={i}>“{cm.text}” <small>{cm.platform} · {cm.modality}{cm.likes ? ` · ${cm.likes} likes` : ""}</small></li>
                        ))}
                    </ul>
                </Section>

                <Section icon={Lightbulb} title="RECOMMENDED CONTENT">
                    {rec ? (
                        <>
                            <p><strong>{rec.title}</strong></p>
                            <p>{rec.content_angle}</p>
                            <p><strong>Target audience:</strong> {rec.target_audience}</p>
                            <p><strong>Outline:</strong></p>
                            <ol className="outline-list">{rec.suggested_sections.map((x, i) => <li key={i}>{x}</li>)}</ol>
                            <div className="format-suggestion"><Video size={14} /><span>Recommended format: <strong>{rec.content_format}</strong></span></div>
                            <p><strong>Expected value:</strong> {rec.expected_value}</p>
                            <p><strong>CTA:</strong> {rec.cta}</p>
                        </>
                    ) : <p className="caveat">No AI recommendation was generated ({o.recommendation_status.replace(/^[a-z_]+: /, "")}).</p>}
                </Section>

                {rec && (
                    <div className="ai-box">
                        <div className="ai-box-title"><Sparkles size={16} /><span>Gemini rationale · confidence {num(rec.confidence, 2)}</span></div>
                        <p>{rec.reason}</p>
                        <ul className="evidence-list">{rec.evidence.map((e) => <li key={e.id}>[{e.id}] “{e.text}” <small>{e.platform}</small></li>)}</ul>
                    </div>
                )}
                <button className="view-button" style={{ marginTop: 16 }} onClick={() => onGenerate(o)}>
                    <span>Generate content brief in Creator Studio</span>
                </button>
            </div>
        </div>
    );
}
