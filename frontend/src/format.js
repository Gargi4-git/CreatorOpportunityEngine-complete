// Presentation helpers only - no business logic or data lives here.
export const num = (v, d = 1) => (v === null || v === undefined ? "n/a" : Number(v).toFixed(d));
export const platformLabel = (share = {}) => {
    const e = Object.entries(share);
    if (!e.length) return "unknown";
    return e.map(([p, v]) => (e.length > 1 ? `${p} ${Math.round(v)}%` : p)).join(" · ");
};
export const platformClass = (share = {}) => {
    const k = Object.keys(share);
    return k.length > 1 ? "platform-mixed" : `platform-${k[0] || "youtube"}`;
};
export const scoreClass = (v) => (v >= 60 ? "score-high" : v >= 35 ? "score-med" : "score-low");
export const oppTitle = (o) => o.recommendation?.title || o.audience_need || o.topic;
