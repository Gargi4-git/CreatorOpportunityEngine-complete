import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend, LineChart, Line } from "recharts";
import { TrendingUp, Sparkles, Layers, Award, CircleAlert } from "lucide-react";
import MetricCard from "../components/MetricCard";
import GhostGapMatrix from "../components/GhostGapMatrix";
import DatasetBanner from "../components/DatasetBanner";
import { num } from "../format";

const COLORS = ["#0f172a", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#64748b", "#14b8a6"];
const Card = ({ title, sub, children, wide }) => (
    <div className={`chart-card ${wide ? "wide" : ""}`}><div className="chart-header"><h3>{title}</h3>{sub && <span>{sub}</span>}</div>{children}</div>
);
const Empty = ({ text }) => <div className="empty-state compact"><CircleAlert size={22} /><p>{text}</p></div>;
const cut = (t) => (String(t).length > 26 ? `${String(t).slice(0, 25)}…` : t);
const HBar = ({ data, x, y }) => data?.length ? (
    <ResponsiveContainer width="100%" height={Math.max(260, data.length * 30)}>
        <BarChart data={data} layout="vertical" margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
            <XAxis type="number" tick={{ fontSize: 11 }} /><YAxis type="category" dataKey={y} width={170} interval={0} tickFormatter={cut} tick={{ fontSize: 11 }} /><Tooltip />
            <Bar dataKey={x} fill="#1e293b" radius={[0, 4, 4, 0]} />
        </BarChart>
    </ResponsiveContainer>) : <Empty text="No data." />;
const Pie_ = ({ data }) => data?.length ? (
    <ResponsiveContainer width="100%" height={240}>
        <PieChart><Pie data={data} dataKey="value" nameKey="name" outerRadius={85} label>{data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>
    </ResponsiveContainer>) : <Empty text="No data." />;

export default function Analytics({ overview: o, onOpenId, onNavigate }) {
    if (!o?.has_data) {
        return <div className="empty-state"><CircleAlert size={36} /><h3>No analysis yet</h3><p>Analytics are computed from your audience data.</p>
            <button className="refresh-button" onClick={() => onNavigate("creator-studio")}>Analyze Audience</button></div>;
    }
    const S = o.summary;
    const palette = {};
    const topTrend = o.topic_trends || [];
    const merged = [];                                 // topic trends -> one wide table for a multi-line chart
    topTrend.forEach((t, k) => t.series.forEach((p) => {
        let row = merged.find((r) => r.period === p.period);
        if (!row) { row = { period: p.period }; merged.push(row); }
        row[t.topic] = p.mentions; palette[t.topic] = COLORS[k % COLORS.length];
    }));
    merged.sort((a, b) => a.period.localeCompare(b.period));

    return (
        <div className="analytics-page">
            <DatasetBanner overview={o} />
            <div className="section-heading"><span className="eyebrow">AUDIENCE INTELLIGENCE REPORT</span><h2>Opportunity Distribution & Insights</h2>
                <p>Every chart below is computed from the analysis stored in MongoDB.</p></div>
            <section className="metric-grid">
                <MetricCard icon={Sparkles} label="Average GhostGap" value={num(S.avg_opportunity_score)} description="Mean across topics" />
                <MetricCard icon={TrendingUp} label="Average Trend" value={S.avg_trend === null ? "n/a" : num(S.avg_trend)} description={S.avg_trend === null ? "Timestamps required" : "Topics with timestamps"} />
                <MetricCard icon={Layers} label="Topics Found" value={S.clustering.clusters} description={`${S.clustering.method}; ${S.clustering.unclustered} unclustered`} />
                <MetricCard icon={Award} label="Top Topic" value={o.top_opportunities[0]?.topic || "n/a"} description={o.top_opportunities[0]?.classification || ""} />
            </section>

            <div className="analytics-charts-grid">
                <Card wide title="GhostGap Matrix — Competition vs Demand" sub="High demand + low supply = Ghost Gap. Click a point for the brief.">
                    <GhostGapMatrix data={o.competition_vs_demand} onSelect={(p) => onOpenId(p.id)} />
                </Card>
                <Card title="Topic Distribution" sub="Comments per topic"><HBar data={o.topic_distribution} x="count" y="topic" /></Card>
                <Card title="Demand by Topic" sub="Demand score 0-100"><HBar data={o.demand_by_topic.filter((d) => d.demand !== null)} x="demand" y="topic" /></Card>
                <Card wide title="Trend over Time" sub={o.trend_over_time.available ? `Mentions per ${o.trend_over_time.granularity}` : ""}>
                    {o.trend_over_time.available ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <LineChart data={merged.length ? merged : o.trend_over_time.series} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis dataKey="period" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Legend />
                                {merged.length ? Object.keys(palette).map((t) => <Line key={t} type="monotone" dataKey={t} stroke={palette[t]} strokeWidth={2} dot={false} />)
                                    : <Line type="monotone" dataKey="mentions" stroke="#0f172a" strokeWidth={2} />}
                            </LineChart>
                        </ResponsiveContainer>
                    ) : <Empty text={o.trend_over_time.reason} />}
                </Card>
                <Card title="Opportunity Score Distribution" sub="Topics per GhostGap range">
                    {o.score_distribution.some((b) => b.count) ? (
                        <ResponsiveContainer width="100%" height={240}><BarChart data={o.score_distribution}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" /><XAxis dataKey="range" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="count" fill="#1e293b" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer>
                    ) : <Empty text="No scored topics." />}
                </Card>
                <Card title="Platform Distribution"><Pie_ data={o.platform_distribution} /></Card>
                <Card title="Sentiment Distribution"><Pie_ data={o.sentiment_distribution} /></Card>
                <Card title="Intent Distribution"><HBar data={o.intent_distribution} x="value" y="name" /></Card>
                <Card title="Top Opportunities">
                    <ol className="top-list">{o.top_opportunities.map((t) => (
                        <li key={t.id}><button onClick={() => onOpenId(t.id)}><span>{t.topic}</span><strong>{num(t.ghostgap)}</strong><em>{t.classification}</em></button></li>))}</ol>
                </Card>
            </div>
        </div>
    );
}
