import React, { useEffect, useMemo, useState } from "react";
import { CircleAlert } from "lucide-react";
import { errMsg, getGraph } from "../api";

const COLUMNS = ["source", "topic", "pain", "opportunity", "content"];
const TITLES = { source: "Source", topic: "Topic", pain: "Pain point", opportunity: "Opportunity", content: "Content" };
const COLOR = { source: "#64748b", topic: "#0f172a", pain: "#ef4444", opportunity: "#10b981", content: "#3b82f6" };
const W = 1180, ROW = 44, PAD_TOP = 54;

export default function Graph({ onOpenId, onNavigate }) {
    const [g, setG] = useState(null);
    const [err, setErr] = useState("");
    const [hover, setHover] = useState(null);
    useEffect(() => { getGraph().then(setG).catch((e) => setErr(errMsg(e))); }, []);

    const layout = useMemo(() => {
        if (!g?.has_data) return null;
        const cols = Object.fromEntries(COLUMNS.map((c) => [c, g.nodes.filter((n) => n.type === c).sort((a, b) => (b.score ?? b.value) - (a.score ?? a.value))]));
        const rows = Math.max(...Object.values(cols).map((c) => c.length), 4);
        const H = PAD_TOP + rows * ROW + 20;
        const pos = {};
        COLUMNS.forEach((c, ci) => cols[c].forEach((n, i) => { pos[n.id] = { x: 110 + ci * ((W - 470) / (COLUMNS.length - 1)), y: PAD_TOP + (i + 0.5) * ((H - PAD_TOP - 20) / cols[c].length) }; }));
        return { pos, H, cols };
    }, [g]);

    if (err) return <div className="ingest-notice-box error"><p>{err}</p></div>;
    if (!g) return null;
    if (!g.has_data) return <div className="empty-state"><CircleAlert size={36} /><h3>No analysis yet</h3><p>The graph is built from your latest analysis.</p>
        <button className="refresh-button" onClick={() => onNavigate("creator-studio")}>Analyze Audience</button></div>;

    const { pos, H } = layout;
    const nbrs = (id) => new Set(g.edges.filter((e) => e.source === id || e.target === id).flatMap((e) => [e.source, e.target]));
    const active = hover ? nbrs(hover) : null;
    const maxW = Math.max(...g.edges.map((e) => e.weight), 1);
    const r = (n) => 5 + Math.min(11, Math.sqrt(Math.max(n.value, 1)) * 1.3);

    return (
        <div className="graph-page">
            <section className="lab-card">
                <div className="graph-legend">{COLUMNS.map((c) => <span key={c}><i style={{ background: COLOR[c] }} />{TITLES[c]}</span>)}
                    <small>Hover to trace connections · click a topic or opportunity to open its brief · node size = evidence / score</small></div>
                <div className="table-scroll"><svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ minWidth: 900 }}>
                    {COLUMNS.map((c, ci) => <text key={c} x={110 + ci * ((W - 470) / 4)} y={24} textAnchor="middle" className="graph-col-title">{TITLES[c].toUpperCase()}</text>)}
                    {g.edges.map((e, i) => {
                        const a = pos[e.source], b = pos[e.target];
                        if (!a || !b) return null;
                        const on = !active || (active.has(e.source) && active.has(e.target) && (e.source === hover || e.target === hover));
                        const mx = (a.x + b.x) / 2;
                        return <path key={i} d={`M${a.x},${a.y} C${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`} fill="none" stroke={COLOR[g.nodes.find((n) => n.id === e.target)?.type] || "#94a3b8"}
                                     strokeWidth={0.8 + (e.weight / maxW) * 4} opacity={on ? 0.45 : 0.06} />;
                    })}
                    {g.nodes.map((n) => {
                        const p = pos[n.id];
                        const dim = active && !active.has(n.id) && n.id !== hover;
                        const clickable = n.opportunity_id && onOpenId;
                        return (
                            <g key={n.id} transform={`translate(${p.x},${p.y})`} opacity={dim ? 0.2 : 1} style={{ cursor: clickable ? "pointer" : "default" }}
                               onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} onClick={() => clickable && onOpenId(n.opportunity_id)}>
                                <circle r={r(n)} fill={COLOR[n.type]} stroke="#fff" strokeWidth={2} />
                                <text x={r(n) + 6} y={4} className="graph-label">{n.label.length > 30 ? `${n.label.slice(0, 29)}…` : n.label}</text>
                                <title>{`${n.label}\nPageRank ${n.pagerank}${n.score != null ? `\nGhostGap ${n.score}` : ""}${n.status ? `\nstatus: ${n.status}` : ""}`}</title>
                            </g>);
                    })}
                </svg></div>
            </section>
            <section className="lab-card">
                <div className="lab-stats">
                    <div className="lab-stat"><span>Nodes / edges</span><strong>{g.metrics.nodes} / {g.metrics.edges}</strong></div>
                    <div className="lab-stat"><span>Most central (PageRank)</span><strong>{g.metrics.most_central}</strong></div>
                    <div className="lab-stat"><span>Pain points shared by several topics</span><strong>{g.metrics.shared_pain_points.length ? g.metrics.shared_pain_points.join(", ") : "none"}</strong></div>
                </div>
                <small className="muted-line">{g.note}</small>
            </section>
        </div>
    );
}
