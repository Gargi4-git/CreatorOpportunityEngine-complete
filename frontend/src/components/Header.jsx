import React from "react";
import { RefreshCw } from "lucide-react";

export default function Header({ activePage, onRefresh, refreshing }) {
    const titles = {
        overview: {
            breadcrumb: "Intelligence / Overview",
            title: "Creator Opportunity Engine",
            subtitle: "Turn audience conversations into validated, high-ROI content opportunities.",
        },
        opportunities: {
            breadcrumb: "Discovery / Opportunities",
            title: "Opportunity Explorer",
            subtitle: "Filter, search, and deep-dive into every audience signal discovered across platforms.",
        },
        sources: {
            breadcrumb: "Pipeline / Data Sources",
            title: "Audience Data Sources",
            subtitle: "Connect YouTube, Reddit, CSV files and media. Status reflects what is actually configured.",
        },
        analytics: {
            breadcrumb: "Insights / Analytics",
            title: "Audience & Topic Analytics",
            subtitle: "Distribution of opportunity scores, momentum trends, and thematic demand.",
        },
    };

    const current = titles[activePage] || titles.overview;

    return (
        <header className="top-header">
            <div>
                <div className="breadcrumb">{current.breadcrumb}</div>
                <h1>{current.title}</h1>
                <p>{current.subtitle}</p>
            </div>

            <button
                className="refresh-button"
                onClick={onRefresh}
                disabled={refreshing}
                title="Reload data from the API"
            >
                <RefreshCw size={16} className={refreshing ? "spin" : ""} />
                <span>{refreshing ? "Refreshing..." : "Refresh"}</span>
            </button>
        </header>
    );
}
