import React from "react";
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, ReferenceArea, ReferenceLine, CartesianGrid, Cell } from "recharts";

const COLOR = { ghost_gap: "#10b981", saturated: "#ef4444", niche: "#3b82f6", low_value: "#94a3b8" };
const LABEL = { ghost_gap: "GHOST GAP", saturated: "SATURATED", niche: "NICHE", low_value: "LOW VALUE" };

/** X = content supply (competition), Y = audience demand. Every point is a real topic from the analysis. */
export default function GhostGapMatrix({ data, onSelect }) {
    if (!data?.available) {
        return <div className="empty-state compact"><p>{data?.reason || "No data."}</p></div>;
    }
    return (
        <div>
            <ResponsiveContainer width="100%" height={380}>
                <ScatterChart margin={{ top: 20, right: 30, bottom: 30, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill="#10b981" fillOpacity={0.08} label={{ value: LABEL.ghost_gap, position: "insideTopLeft", fill: "#059669", fontSize: 11, fontWeight: 700 }} />
                    <ReferenceArea x1={50} x2={100} y1={50} y2={100} fill="#ef4444" fillOpacity={0.05} label={{ value: LABEL.saturated, position: "insideTopRight", fill: "#dc2626", fontSize: 11, fontWeight: 700 }} />
                    <ReferenceArea x1={0} x2={50} y1={0} y2={50} fill="#3b82f6" fillOpacity={0.04} label={{ value: LABEL.niche, position: "insideBottomLeft", fill: "#2563eb", fontSize: 11, fontWeight: 700 }} />
                    <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill="#94a3b8" fillOpacity={0.06} label={{ value: LABEL.low_value, position: "insideBottomRight", fill: "#64748b", fontSize: 11, fontWeight: 700 }} />
                    <ReferenceLine x={50} stroke="#94a3b8" strokeDasharray="4 4" />
                    <ReferenceLine y={50} stroke="#94a3b8" strokeDasharray="4 4" />
                    <XAxis type="number" dataKey="competition" domain={[0, 100]} name="Competition" label={{ value: "Content supply / competition →", position: "insideBottom", offset: -15, fontSize: 12 }} tick={{ fontSize: 11 }} />
                    <YAxis type="number" dataKey="demand" domain={[0, 100]} name="Demand" label={{ value: "Audience demand →", angle: -90, position: "insideLeft", fontSize: 12 }} tick={{ fontSize: 11 }} />
                    <ZAxis type="number" dataKey="evidence" range={[60, 400]} name="Comments" />
                    <Tooltip cursor={{ strokeDasharray: "3 3" }} content={({ active, payload }) => active && payload?.length ? (
                        <div className="custom-chart-tooltip">
                            <p className="tooltip-rank">{payload[0].payload.topic}</p>
                            <p>Demand {payload[0].payload.demand} · Competition {payload[0].payload.competition}</p>
                            <p>GhostGap {payload[0].payload.ghostgap} · {payload[0].payload.evidence} comments</p>
                        </div>) : null} />
                    <Scatter data={data.points} onClick={(p) => onSelect?.(p)}>
                        {data.points.map((p) => <Cell key={p.id} fill={COLOR[p.quadrant]} style={{ cursor: onSelect ? "pointer" : "default" }} />)}
                    </Scatter>
                </ScatterChart>
            </ResponsiveContainer>
            <p className="chart-note">Competition is measured from live YouTube search results for the highest-demand topics; topics without a measurement are not plotted.</p>
        </div>
    );
}
