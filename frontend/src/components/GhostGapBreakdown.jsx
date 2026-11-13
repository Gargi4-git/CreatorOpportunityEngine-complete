import React from "react";

const NAMES = { demand: "Demand", trend: "Trend", pain: "Pain", engagement: "Engagement", freshness: "Freshness", competition: "Competition" };

/** Visual per-component breakdown of the GhostGap score (points earned / max points). */
export default function GhostGapBreakdown({ breakdown, score, classification }) {
    if (!breakdown) return null;
    return (
        <div className="gg-breakdown">
            <div className="gg-total"><span>GhostGap Score</span><strong>{score ?? "n/a"}</strong><em>{classification}</em></div>
            {Object.entries(breakdown).map(([k, b]) => {
                const neg = b.weight < 0;
                const pct = b.points === null ? 0 : (Math.abs(b.points) / b.max_points) * 100;
                return (
                    <div key={k} className={`gg-row ${b.points === null ? "na" : ""}`}>
                        <span className="gg-name">{NAMES[k]}</span>
                        <div className="gg-track"><div className={`gg-fill ${neg ? "neg" : ""}`} style={{ width: `${pct}%` }} /></div>
                        <span className="gg-pts">
                            {b.points === null ? "unavailable" : `${neg ? "−" : ""}${Math.abs(b.points)} / ${b.max_points}`}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
