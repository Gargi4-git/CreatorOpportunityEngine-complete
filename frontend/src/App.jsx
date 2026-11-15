import React, { useCallback, useEffect, useState } from "react";
import { getAnalysis, getHealth, getOpportunities, getOpportunity, getOverview } from "./api";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import OpportunityModal from "./components/OpportunityModal";
import Overview from "./pages/Overview";
import Opportunities from "./pages/Opportunities";
import Sources from "./pages/Sources";
import Analytics from "./pages/Analytics";
import Evaluation from "./pages/Evaluation";
import Lab from "./pages/Lab";
import History from "./pages/History";
import Planner from "./pages/Planner";
import Graph from "./pages/Graph";
import CreatorStudio from "./CreatorStudio";
import { RefreshCw, CircleAlert } from "lucide-react";
import "./App.css";
import "./live.css";

export default function App() {
    const [activePage, setActivePage] = useState("overview");
    const [health, setHealth] = useState(null);
    const [overview, setOverview] = useState(null);       // GET /api/analytics/overview (null until loaded)
    const [opportunities, setOpportunities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [backendDown, setBackendDown] = useState(false);
    const [selected, setSelected] = useState(null);       // opportunity open in the detail modal
    const [studioOppId, setStudioOppId] = useState(null); // opportunity chosen for the content generator
    const [run, setRun] = useState(null);                 // {id, label, analysis}

    const loadData = useCallback(async () => {
        setRefreshing(true);
        try {
            const [h, ov, opps] = await Promise.all([getHealth(), getOverview(), getOpportunities()]);
            setHealth(h); setOverview(ov); setOpportunities(opps.opportunities || []); setBackendDown(false);
        } catch {
            setBackendDown(true);
        } finally {
            setLoading(false); setRefreshing(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    // Poll the real analysis job until it finishes, then refresh every page from the API.
    useEffect(() => {
        if (!run?.id || ["completed", "failed"].includes(run.analysis?.status)) return undefined;
        const t = setInterval(async () => {
            try {
                const a = await getAnalysis(run.id);
                setRun((r) => (r && r.id === run.id ? { ...r, analysis: a } : r));
                if (a.status === "completed") loadData();
            } catch { /* transient network error: keep polling */ }
        }, 1000);
        return () => clearInterval(t);
    }, [run?.id, run?.analysis?.status, loadData]);

    const startRun = (id, label) => setRun({ id, label, analysis: null });

    const openOppById = async (id) => {                    // from graph / planner / lab: the opportunity may belong to any analysis
        const local = opportunities.find((o) => o.id === id);
        if (local) return setSelected(local);
        try { setSelected(await getOpportunity(id)); } catch { /* opportunity no longer exists */ }
    };

    const openStudio = (opp) => { setStudioOppId(opp?.id || null); setActivePage("creator-studio"); setSelected(null); };

    return (
        <div className="app-shell">
            <Sidebar activePage={activePage} setActivePage={setActivePage} signalCount={opportunities.length} health={health} backendDown={backendDown} />
            <main className="main-content">
                {activePage !== "creator-studio" && <Header activePage={activePage} onRefresh={loadData} refreshing={refreshing} />}
                {loading ? (
                    <div className="loading-state"><RefreshCw size={28} className="spin" /><p>Loading Creator Audience Intelligence...</p></div>
                ) : backendDown ? (
                    <div className="empty-state error-banner">
                        <CircleAlert size={36} color="#ef4444" />
                        <h3>Backend Connection Error</h3>
                        <p>Cannot reach the API. Start it with <code>uvicorn app.main:app --reload</code> and check that MongoDB is running.</p>
                        <button className="refresh-button" onClick={loadData}>Retry Connection</button>
                    </div>
                ) : (
                    <>
                        {activePage === "overview" && <Overview overview={overview} opportunities={opportunities} onOpen={setSelected} onNavigate={setActivePage} />}
                        {activePage === "opportunities" && <Opportunities opportunities={opportunities} overview={overview} onOpen={setSelected} onNavigate={setActivePage} />}
                        {activePage === "creator-studio" && (
                            <CreatorStudio health={health} run={run} startRun={startRun} opportunities={opportunities}
                                           studioOppId={studioOppId} setStudioOppId={setStudioOppId} />
                        )}
                        {activePage === "sources" && <Sources health={health} run={run} startRun={startRun} overview={overview} />}
                        {activePage === "evaluation" && <Evaluation opportunities={opportunities} />}
                        {activePage === "lab" && <Lab overview={overview} onNavigate={setActivePage} />}
                        {activePage === "history" && <History onNavigate={setActivePage} />}
                        {activePage === "planner" && <Planner opportunities={opportunities} onNavigate={setActivePage} onOpenOpp={openOppById} />}
                        {activePage === "graph" && <Graph onOpenId={openOppById} onNavigate={setActivePage} />}
                        {activePage === "analytics" && <Analytics overview={overview} onOpenId={openOppById} onNavigate={setActivePage} />}
                    </>
                )}
            </main>
            <OpportunityModal opportunity={selected} onClose={() => setSelected(null)} onGenerate={openStudio} />
        </div>
    );
}
