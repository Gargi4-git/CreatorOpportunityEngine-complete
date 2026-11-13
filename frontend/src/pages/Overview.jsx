import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { MessageSquareText, Users, Sparkles, TrendingUp, ArrowRight, CircleAlert } from "lucide-react";
import MetricCard from "../components/MetricCard";
import OpportunityCard from "../components/OpportunityCard";
import DatasetBanner from "../components/DatasetBanner";
import { num } from "../format";

export default function Overview({ overview, opportunities, onOpen, onNavigate }) {
    if (!overview?.has_data) {
        return (
            <div className="empty-state">
                <CircleAlert size={36} />
                <h3>No analysis yet</h3>
                <p>Analyze a YouTube video, Reddit community, CSV file or media upload to see real audience opportunities here.</p>
                <button className="refresh-button" onClick={() => onNavigate("creator-studio")}>Analyze Audience</button>
            </div>
        );
    }
    const S = overview.summary;
    const chart = opportunities.slice(0, 8).map((o) => ({ name: `#${o.rank}`, topic: o.topic, score: o.scores.ghostgap ?? 0 }));
    return (
        <div className="overview-page">
            <DatasetBanner overview={overview} />
            <section className="metric-grid">
                <MetricCard icon={MessageSquareText} label="Audience Comments" value={S.audience_comments.toLocaleString()}
                            description={`After cleaning (${S.data_quality.raw} raw records)`} />
                <MetricCard icon={Users} label="Total Engagement" value={S.total_engagement.toLocaleString()}
                            description={S.total_engagement ? "Likes + replies in the data" : "No engagement data in this source"} />
                <MetricCard icon={Sparkles} label="Avg Opportunity Score" value={num(S.avg_opportunity_score)} description="Mean GhostGap across topics" />
                <MetricCard icon={TrendingUp} label="Avg Trend Momentum" value={S.avg_trend === null ? "n/a" : num(S.avg_trend)}
                            description={S.avg_trend === null ? "Trend unavailable — timestamps required" : "Topics with timestamps only"} />
            </section>
            <section className="chart-section">
                <div className="section-heading"><div>
                    <span className="eyebrow">INTELLIGENCE RADAR</span>
                    <h2>Opportunity Strength Distribution</h2>
                    <p>GhostGap score of the top topics found in your audience data.</p>
                </div></div>
                <div className="chart-wrapper">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chart} margin={{ top: 15, right: 20, left: -10, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                            <XAxis dataKey="name" stroke="#6b7280" tick={{ fontSize: 12 }} /><YAxis domain={[0, 100]} stroke="#6b7280" tick={{ fontSize: 12 }} />
                            <Tooltip content={({ active, payload }) => active && payload?.length ? (
                                <div className="custom-chart-tooltip"><p className="tooltip-rank">{payload[0].payload.name}: {payload[0].payload.topic}</p>
                                    <p>GhostGap: <strong>{payload[0].payload.score.toFixed(1)}</strong></p></div>) : null} />
                            <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                                {chart.map((e, i) => <Cell key={i} fill={e.score > 60 ? "#111827" : e.score > 35 ? "#374151" : "#6b7280"} />)}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </section>
            <section className="opportunities-section">
                <div className="section-heading opportunities-heading">
                    <div><span className="eyebrow">HIGH ROI SIGNALS</span><h2>Top Creator Opportunities</h2>
                        <p>Ranked by GhostGap: demand, trend, pain, engagement and freshness, minus competition.</p></div>
                    <button className="view-all-btn" onClick={() => onNavigate("opportunities")}><span>View All {opportunities.length} Signals</span><ArrowRight size={15} /></button>
                </div>
                <div className="opportunity-list">
                    {opportunities.slice(0, 6).map((o) => <OpportunityCard key={o.id} opportunity={o} rank={o.rank} onOpen={onOpen} />)}
                </div>
            </section>
        </div>
    );
}
