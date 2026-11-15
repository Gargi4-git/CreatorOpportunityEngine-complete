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
        evaluation: {
            breadcrumb: "Research / Evaluation",
            title: "Evaluation & Validation",
            subtitle: "Measure classifier and clustering quality against your own labels, and test whether GhostGap predicts real results.",
        },
        lab: {
            breadcrumb: "Research / GhostGap Lab",
            title: "GhostGap Lab",
            subtitle: "Change the weights, watch the ranking move, and see how stable the top opportunity really is.",
        },
        history: {
            breadcrumb: "Research / History",
            title: "Analysis History & Comparison",
            subtitle: "Compare two analyses side by side, or follow topics across analyses of the same source over time.",
        },
        graph: {
            breadcrumb: "Research / Knowledge Graph",
            title: "Audience Knowledge Graph",
            subtitle: "Source → Topic → Pain point, Topic → Opportunity → Content, built from your analysis.",
        },
        planner: {
            breadcrumb: "Workspace / Content Planner",
            title: "Content Planner",
            subtitle: "Move opportunities from idea to scripted to published, and track how each one performs.",
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
