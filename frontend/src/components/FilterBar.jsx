import React from "react";
import { Search, Filter, ArrowUpDown, X } from "lucide-react";

export default function FilterBar({
    search,
    setSearch,
    selectedPlatform,
    setSelectedPlatform,
    selectedTopic,
    setSelectedTopic,
    sortBy,
    setSortBy,
    minScore,
    setMinScore,
    topics = [],
    availablePlatforms = [],
    totalCount = 0,
    filteredCount = 0,
}) {
    const platforms = [{ id: "all", label: "All Platforms" }, ...availablePlatforms.map((p) => ({ id: p, label: p.charAt(0).toUpperCase() + p.slice(1) }))];

    const sortOptions = [
        { id: "opportunity", label: "Highest Opportunity" },
        { id: "demand", label: "Highest Demand" },
        { id: "trend", label: "Highest Trend" },
        { id: "competition", label: "Lowest Competition" },
        { id: "newest", label: "Newest" },
    ];

    const hasActiveFilters =
        search !== "" ||
        selectedPlatform !== "all" ||
        selectedTopic !== "all" ||
        minScore > 0 ||
        sortBy !== "opportunity";

    const resetFilters = () => {
        setSearch("");
        setSelectedPlatform("all");
        setSelectedTopic("all");
        setSortBy("opportunity");
        setMinScore(0);
    };

    return (
        <div className="filter-bar">
            {/* Top row: Search and platform chips */}
            <div className="filter-top-row">
                <div className="search-box">
                    <Search size={16} />
                    <input
                        type="text"
                        placeholder="Search topics..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    {search && (
                        <button
                            className="clear-search-btn"
                            onClick={() => setSearch("")}
                            title="Clear search"
                        >
                            <X size={14} />
                        </button>
                    )}
                </div>

                <div className="platform-chips">
                    {platforms.map((p) => (
                        <button
                            key={p.id}
                            className={`platform-chip ${
                                selectedPlatform === p.id ? "active" : ""
                            }`}
                            onClick={() => setSelectedPlatform(p.id)}
                        >
                            {p.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Bottom row: Dropdowns for Topic, Sort, Min Score, and Filter Reset */}
            <div className="filter-bottom-row">
                <div className="filter-select-group">
                    <div className="select-wrapper">
                        <Filter size={14} className="select-icon" />
                        <select
                            value={selectedTopic}
                            onChange={(e) => setSelectedTopic(e.target.value)}
                            className="filter-select"
                        >
                            <option value="all">All Topics ({topics.length})</option>
                            {topics.map((t) => (
                                <option key={t} value={t}>
                                    {t}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="select-wrapper">
                        <ArrowUpDown size={14} className="select-icon" />
                        <select
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value)}
                            className="filter-select"
                        >
                            {sortOptions.map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="min-score-filter">
                        <span>Min Score:</span>
                        <div className="score-preset-buttons">
                            {[0, 30, 50, 70].map((val) => (
                                <button
                                    key={val}
                                    className={`score-preset-btn ${
                                        minScore === val ? "active" : ""
                                    }`}
                                    onClick={() => setMinScore(val)}
                                >
                                    {val === 0 ? "All" : `>${val}`}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="filter-meta">
                    <span className="results-count">
                        Showing <strong>{filteredCount}</strong> of {totalCount} signals
                    </span>
                    {hasActiveFilters && (
                        <button className="reset-filters-btn" onClick={resetFilters}>
                            Reset Filters
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
