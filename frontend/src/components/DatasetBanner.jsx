import React from "react";
import { FlaskConical } from "lucide-react";

/** Always tells the user when the displayed analysis came from the synthetic demo dataset. */
export default function DatasetBanner({ overview }) {
    if (!overview?.has_data || !overview.dataset_labels?.includes("demo")) return null;
    return (
        <div className="demo-banner">
            <FlaskConical size={16} />
            <div><strong>Demo Dataset</strong> — a synthetic sample, not live audience data. It ran through the same pipeline as real data.</div>
        </div>
    );
}
