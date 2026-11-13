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
export const runAnalysis = (sourceIds) => API.post("/analysis/run", { source_ids: sourceIds }).then((r) => r.data);

export const analyzeYoutube = (url, commentLimit) =>
    API.post("/sources/youtube/analyze", { url, comment_limit: commentLimit }, { timeout: 180000 }).then((r) => r.data);
export const analyzeReddit = (target, limit) =>
    API.post("/sources/reddit/analyze", { target, limit }, { timeout: 120000 }).then((r) => r.data);
export const loadDemo = () => API.post("/sources/demo/load").then((r) => r.data);

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
