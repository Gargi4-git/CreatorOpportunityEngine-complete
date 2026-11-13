import React, { useMemo, useState } from "react";
import FilterBar from "../components/FilterBar";
import OpportunityCard from "../components/OpportunityCard";
import DatasetBanner from "../components/DatasetBanner";
import { CircleAlert } from "lucide-react";

const KEY = { opportunity: (o) => o.scores.ghostgap, demand: (o) => o.scores.demand, trend: (o) => o.scores.trend,
              competition: (o) => o.scores.competition, newest: (o) => o.created_at };

export default function Opportunities({ opportunities = [], overview, onOpen, onNavigate }) {
    const [search, setSearch] = useState("");
    const [platform, setPlatform] = useState("all");
    const [topic, setTopic] = useState("all");
    const [sortBy, setSortBy] = useState("opportunity");
    const [minScore, setMinScore] = useState(0);

    const topics = useMemo(() => [...new Set(opportunities.map((o) => o.topic))].sort(), [opportunities]);
    const platforms = useMemo(() => [...new Set(opportunities.flatMap((o) => Object.keys(o.platform_share)))].sort(), [opportunities]);

    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        const list = opportunities.filter((o) =>
            (platform === "all" || platform in o.platform_share) && (topic === "all" || o.topic === topic) &&
            (o.scores.ghostgap ?? 0) >= minScore &&
            (!q || [o.topic, o.audience_need, o.recommendation?.title].filter(Boolean).join(" ").toLowerCase().includes(q)));
        const key = KEY[sortBy];
        const asc = sortBy === "competition";            // lowest competition first; missing values always last
        return [...list].sort((a, b) => {
            const x = key(a), y = key(b);
            if (x === null || x === undefined) return 1;
            if (y === null || y === undefined) return -1;
            if (sortBy === "newest") return String(y).localeCompare(String(x));
            return asc ? x - y : y - x;
        });
    }, [opportunities, search, platform, topic, sortBy, minScore]);

    if (!opportunities.length) {
        return (
            <div className="empty-state"><CircleAlert size={36} /><h3>No opportunities yet</h3>
                <p>Run an analysis to discover content opportunities from real audience data.</p>
                <button className="refresh-button" onClick={() => onNavigate("creator-studio")}>Analyze Audience</button></div>
        );
    }
    return (
        <div className="opportunities-page">
            <DatasetBanner overview={overview} />
            <div className="page-header"><div className="section-heading">
                <span className="eyebrow">DISCOVERY & FILTRATION</span><h2>Opportunity Explorer</h2>
                <p>Search, sort, and segment audience opportunities by platform and topic.</p></div></div>
            <FilterBar search={search} setSearch={setSearch} selectedPlatform={platform} setSelectedPlatform={setPlatform}
                       selectedTopic={topic} setSelectedTopic={setTopic} sortBy={sortBy} setSortBy={setSortBy} minScore={minScore}
                       setMinScore={setMinScore} topics={topics} availablePlatforms={platforms}
                       totalCount={opportunities.length} filteredCount={filtered.length} />
            {filtered.length ? (
                <div className="opportunity-list">{filtered.map((o, i) => <OpportunityCard key={o.id} opportunity={o} rank={sortBy === "opportunity" ? o.rank : i + 1} onOpen={onOpen} />)}</div>
            ) : (
                <div className="empty-state"><CircleAlert size={36} /><h3>No matching opportunities found</h3><p>Try clearing your search or relaxing the topic / score filters.</p></div>
            )}
        </div>
    );
}
