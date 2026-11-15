import axios from "axios";

// Only a public API URL lives in the frontend. No keys or secrets ever do.
export const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const API = axios.create({ baseURL: `${API_BASE}/api`, timeout: 60000 });

/** Turn any failure into a short, human-readable message (never a stack trace). */
export function errMsg(e) {
    if (e?.code === "ECONNABORTED") return "The request took too long. Please try again.";
    if (!e?.response) return "Cannot reach the backend. Make sure the API server is running.";
    const d = e.response.data?.detail;
    if (typeof d === "string") return d;
    if (d?.message) return d.message;
    if (Array.isArray(d)) return "Invalid input. Please check the fields and try again.";
    return `Request failed (HTTP ${e.response.status}).`;
}
export const errCode = (e) => e?.response?.data?.detail?.code;

export const getHealth = () => API.get("/health").then((r) => r.data);
export const getOverview = (id) => API.get("/analytics/overview", { params: id ? { analysis_id: id } : {} }).then((r) => r.data);
export const getOpportunities = (params = {}) => API.get("/opportunities", { params }).then((r) => r.data);
export const getOpportunity = (id) => API.get(`/opportunities/${id}`).then((r) => r.data);
export const getSources = () => API.get("/sources").then((r) => r.data.sources);
export const getSource = (id) => API.get(`/sources/${id}`).then((r) => r.data);
export const getAnalysis = (id) => API.get(`/analysis/${id}`).then((r) => r.data);
export const runAnalysis = (sourceIds, multilingual = false) => API.post("/analysis/run", { source_ids: sourceIds, multilingual }).then((r) => r.data);

export const analyzeYoutube = (url, commentLimit, multilingual = false) =>
    API.post("/sources/youtube/analyze", { url, comment_limit: commentLimit, multilingual }, { timeout: 180000 }).then((r) => r.data);
export const analyzeYoutubeChannel = (url, videoCount, commentsPerVideo, multilingual = false) =>
    API.post("/sources/youtube/channel/analyze", { url, video_count: videoCount, comments_per_video: commentsPerVideo, multilingual }, { timeout: 300000 }).then((r) => r.data);
export const analyzeReddit = (target, limit, multilingual = false) =>
    API.post("/sources/reddit/analyze", { target, limit, multilingual }, { timeout: 120000 }).then((r) => r.data);
export const loadDemo = (multilingual = false) => API.post("/sources/demo/load", null, { params: { multilingual } }).then((r) => r.data);

const upload = (path, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return API.post(path, fd, { timeout: 300000 }).then((r) => r.data);
};
export const uploadCsv = (f) => upload("/sources/csv/upload", f);
export const uploadImage = (f) => upload("/sources/image/analyze", f);
export const uploadAudio = (f) => upload("/sources/audio/analyze", f);
export const uploadVideo = (f) => upload("/sources/video/analyze", f);

export const generateBrief = (opportunityId, format) =>
    API.post("/creator-studio/generate", { opportunity_id: opportunityId, format }, { timeout: 120000 }).then((r) => r.data);
export const searchAudience = (q) => API.get("/search", { params: { q } }).then((r) => r.data);

// ---- evaluation (hand labels, metrics, ablation, embedder comparison)
export const evalOptions = () => API.get("/evaluation/options").then((r) => r.data);
export const evalSample = (n = 20) => API.get("/evaluation/sample", { params: { n } }).then((r) => r.data);
export const evalSaveLabels = (items) => API.post("/evaluation/labels", items).then((r) => r.data);
export const evalLabels = () => API.get("/evaluation/labels").then((r) => r.data);
export const evalClearLabels = () => API.delete("/evaluation/labels").then((r) => r.data);
export const evalImportLabels = (f) => upload("/evaluation/labels/import", f);
export const evalReport = () => API.get("/evaluation/report", { timeout: 120000 }).then((r) => r.data);
export const evalCompareEmbedders = () => API.post("/evaluation/compare-embedders", null, { timeout: 300000 }).then((r) => r.data);

// ---- GhostGap lab
export const labWeights = () => API.get("/lab/weights").then((r) => r.data);
export const labRescore = (weights, sensitivity = false, spread = 0.3) =>
    API.post("/lab/rescore", { weights, sensitivity, spread, draws: 500 }, { timeout: 120000 }).then((r) => r.data);
export const labLearn = () => API.post("/lab/learn").then((r) => r.data);

// ---- closed-loop validation
export const valList = () => API.get("/validation").then((r) => r.data.items);
export const valTrack = (opportunityId, videoUrl) => API.post("/validation/track", { opportunity_id: opportunityId, video_url: videoUrl || null }).then((r) => r.data);
export const valMetrics = (id, views, baseline) => API.post(`/validation/${id}/metrics`, { views, baseline_views: baseline }).then((r) => r.data);
export const valRefresh = (id) => API.post(`/validation/${id}/refresh`, null, { timeout: 120000 }).then((r) => r.data);
export const valDelete = (id) => API.delete(`/validation/${id}`).then((r) => r.data);
export const valReport = (includeImmature = false) => API.get("/validation/report", { params: { include_immature: includeImmature } }).then((r) => r.data);

// ---- history / compare
export const historyList = () => API.get("/history").then((r) => r.data);
export const historyCompare = (a, b, threshold = 0.5) => API.get("/history/compare", { params: { a, b, threshold } }).then((r) => r.data);
export const historySeries = (sourceKey) => API.get("/history/series", { params: { source_key: sourceKey } }).then((r) => r.data);

// ---- planner
export const planList = () => API.get("/planner").then((r) => r.data);
export const planCreate = (opportunityId, extra = {}) => API.post("/planner", { opportunity_id: opportunityId, ...extra }).then((r) => r.data);
export const planUpdate = (id, patch) => API.patch(`/planner/${id}`, patch).then((r) => r.data);
export const planPublish = (id, videoUrl) => API.post(`/planner/${id}/publish`, { video_url: videoUrl }).then((r) => r.data);
export const planDelete = (id) => API.delete(`/planner/${id}`).then((r) => r.data);

// ---- knowledge graph
export const getGraph = () => API.get("/graph").then((r) => r.data);
