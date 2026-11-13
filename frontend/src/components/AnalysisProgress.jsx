import React from "react";
import { CheckCircle2, Circle, MinusCircle, XCircle, Loader2 } from "lucide-react";

const ICON = {
    done: <CheckCircle2 size={16} className="st-done" />,
    running: <Loader2 size={16} className="st-run spin" />,
    skipped: <MinusCircle size={16} className="st-skip" />,
    pending: <Circle size={16} className="st-pend" />,
};

/** Renders the REAL step list returned by GET /api/analysis/{id}. */
export default function AnalysisProgress({ run }) {
    if (!run) return null;
    const a = run.analysis;
    if (!a) return <div className="progress-card"><Loader2 size={16} className="spin" /> Starting analysis…</div>;
    const q = a.summary?.data_quality;
    return (
        <div className="progress-card">
            <div className="progress-head">
                <strong>
                    {a.status === "completed" ? "Analysis Complete" : a.status === "failed" ? "Analysis failed" : "Analyzing audience…"}
                </strong>
                <span>{run.label}</span>
            </div>
            <div className="progress-bar"><div className={`progress-fill ${a.status}`} style={{ width: `${a.progress || 0}%` }} /></div>
            {a.status === "failed" && <div className="progress-error"><XCircle size={15} /> {a.error}</div>}
            <ul className="step-list">
                {a.steps.map((s) => (
                    <li key={s.key} className={`step-${s.status}`}>
                        {ICON[s.status]}
                        <div>
                            <span>{s.label}</span>
                            {s.detail && <small>{s.detail}</small>}
                        </div>
                    </li>
                ))}
            </ul>
            {q && (
                <div className="quality-grid">
                    {[["Raw records", q.raw], ["After cleaning", q.raw - q.empty_removed - q.too_short_removed - q.spam_removed - q.duplicates_removed - q.non_english_removed],
                      ["Duplicates removed", q.duplicates_removed + q.near_duplicates_removed], ["Spam removed", q.spam_removed], ["Analyzed", q.analyzed]]
                        .map(([k, v]) => <div key={k}><strong>{v}</strong><span>{k}</span></div>)}
                </div>
            )}
            {a.summary?.warnings?.length > 0 && (
                <ul className="warn-list">{a.summary.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
            )}
        </div>
    );
}
