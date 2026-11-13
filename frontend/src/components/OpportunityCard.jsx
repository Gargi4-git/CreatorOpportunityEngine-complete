import React from "react";
import { ChevronRight, MessageSquareText, Zap, Video } from "lucide-react";
import { num, oppTitle, platformClass, platformLabel, scoreClass } from "../format";

export default function OpportunityCard({ opportunity: o, rank, onOpen }) {
    const s = o.scores;
    const mods = Object.keys(o.modality_mix || {}).filter((m) => m !== "text");
    return (
        <div className="opportunity-card">
            <div className="opportunity-top">
                <div className="rank-topic">
                    <span className="rank">#{rank}</span>
                    <span className="topic-badge">{o.topic}</span>
                    <span className={`platform-pill ${platformClass(o.platform_share)}`}>{platformLabel(o.platform_share)}</span>
                    {mods.length > 0 && <span className="format-badge"><Video size={11} />{["text", ...mods].join(" + ")}</span>}
                </div>
                <div className={`score-block ${scoreClass(s.ghostgap ?? 0)}`}>
                    <span>Opportunity</span>
                    <strong>{num(s.ghostgap)}</strong>
                </div>
            </div>
            <h3>{oppTitle(o)}</h3>
            <p className="opportunity-description">
                {o.recommendation?.reason || o.audience_need || o.explanation?.verdict}
            </p>
            <div className="score-chips">
                {[["Demand", s.demand], ["Trend", s.trend], ["Pain", s.pain], ["Competition", s.competition]].map(([k, v]) => (
                    <span key={k} className={v === null ? "na" : ""}>{k} <strong>{num(v, 0)}</strong></span>
                ))}
            </div>
            <div className="opportunity-meta">
                <span><MessageSquareText size={13} />{o.evidence_count} comments</span>
                <span><Zap size={13} />{o.total_engagement.toLocaleString()} engagement</span>
                <span className="confidence-pill">{s.classification}</span>
                {o.recommendation_status !== "generated" && <span className="muted-pill" title={o.recommendation_status}>no AI recommendation</span>}
            </div>
            <button className="view-button" onClick={() => onOpen(o)}>
                <span>View Opportunity Brief</span><ChevronRight size={15} />
            </button>
        </div>
    );
}
