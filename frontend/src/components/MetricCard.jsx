import React from "react";

export default function MetricCard({ icon: Icon, label, value, description, trend }) {
    return (
        <div className="metric-card">
            <div className="metric-icon">
                <Icon size={20} />
            </div>

            <div className="metric-content">
                <p>{label}</p>
                <h2>{value}</h2>
                <div className="metric-footer">
                    {description && <span>{description}</span>}
                    {trend && <span className="metric-trend">{trend}</span>}
                </div>
            </div>
        </div>
    );
}
