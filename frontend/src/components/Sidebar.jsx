import React from "react";
import { LayoutDashboard, Sparkles, Database, BarChart3, Brain, Wand2 } from "lucide-react";

const Chip = ({ ok, label }) => <li className={ok ? "ok" : "off"}><span />{label}</li>;

export default function Sidebar({ activePage, setActivePage, signalCount = 0, health, backendDown }) {
    const menuItems = [
        { id: "overview", label: "Overview", icon: LayoutDashboard },
        { id: "opportunities", label: "Opportunities", icon: Sparkles, badge: signalCount > 0 ? signalCount : null },
        { id: "creator-studio", label: "Creator Studio", icon: Wand2, badge: "NEW" },
        { id: "sources", label: "Data Sources", icon: Database },
        { id: "analytics", label: "Analytics", icon: BarChart3 },
    ];
    return (
        <aside className="sidebar">
            <div className="brand">
                <div className="brand-mark"><Brain size={22} /></div>
                <div><h1>Creator Engine</h1><span>Audience Intelligence</span></div>
            </div>
            <nav className="sidebar-nav">
                <div className="nav-label">WORKSPACE</div>
                {menuItems.map((item) => {
                    const Icon = item.icon;
                    return (
                        <button key={item.id} className={`nav-item ${activePage === item.id ? "active" : ""}`} onClick={() => setActivePage(item.id)}>
                            <Icon size={18} /><span>{item.label}</span>
                            {item.badge && <span className="nav-badge">{item.badge}</span>}
                        </button>
                    );
                })}
            </nav>
            <div className="sidebar-bottom">
                <div className="system-status">
                    <span className={`status-dot ${backendDown ? "down" : ""}`}></span>
                    <div>
                        <strong>{backendDown ? "Backend offline" : "API online"}</strong>
                        <small>Live system state</small>
                    </div>
                </div>
                {health && !backendDown && (
                    <ul className="status-list">
                        <Chip
                            ok={health?.database === "local" || health?.database === "mongodb" || Boolean(health?.mongodb?.connected)}
                            label={
                                health?.database === "local"
                                    ? "Local storage (no MongoDB)"
                                    : (health?.database === "mongodb" || health?.mongodb?.connected)
                                        ? "MongoDB connected"
                                        : "MongoDB unavailable"
                            }
                        />
                        <Chip ok={true} label="Demo Dataset available" />
                        <Chip
                            ok={Boolean(health?.embeddings?.available)}
                            label={health?.embeddings?.available ? "Embeddings ready" : "Embeddings unavailable"}
                        />
                        <Chip
                            ok={Boolean(health?.gemini?.configured)}
                            label={health?.gemini?.message || (health?.gemini?.configured ? "Gemini configured" : "Gemini not configured")}
                        />
                        <Chip
                            ok={Boolean(health?.youtube?.configured)}
                            label={health?.youtube?.message || (health?.youtube?.configured ? "YouTube API connected" : "YouTube API not connected")}
                        />
                        <Chip
                            ok={Boolean(health?.reddit?.configured)}
                            label={health?.reddit?.message || (health?.reddit?.configured ? "Reddit connected" : "Reddit integration unavailable")}
                        />
                        <Chip
                            ok={Boolean(health?.whisper?.available)}
                            label={health?.whisper?.message || (health?.whisper?.available ? "Whisper ready" : "Whisper unavailable")}
                        />
                    </ul>
                )}
            </div>
        </aside>
    );
}
