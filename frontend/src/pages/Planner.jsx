import React, { useCallback, useEffect, useState } from "react";
import { CircleAlert, ChevronLeft, ChevronRight, Trash2, ExternalLink } from "lucide-react";
import { errMsg, planCreate, planDelete, planList, planPublish, planUpdate } from "../api";

const COLS = [["idea", "Idea"], ["scripted", "Scripted"], ["published", "Published"]];

export default function Planner({ opportunities, onNavigate, onOpenOpp }) {
    const [items, setItems] = useState([]);
    const [err, setErr] = useState("");
    const [oppId, setOppId] = useState("");
    const [edit, setEdit] = useState(null);       // item being edited
    const [pub, setPub] = useState({});            // item id -> publish url draft

    const load = useCallback(async () => { try { setItems((await planList()).items); } catch (e) { setErr(errMsg(e)); } }, []);
    useEffect(() => { load(); }, [load]);
    const act = async (fn) => { setErr(""); try { await fn(); await load(); } catch (e) { setErr(errMsg(e)); } };

    return (
        <div className="planner-page">
            {err && <div className="ingest-notice-box error"><span>⚠️</span><div><p>{err}</p></div></div>}
            <section className="lab-card">
                <div className="btn-row">
                    <select value={oppId} onChange={(e) => setOppId(e.target.value)}><option value="">Add an opportunity as an idea…</option>
                        {opportunities.map((o) => <option key={o.id} value={o.id}>#{o.rank} {o.topic} (GhostGap {o.scores.ghostgap})</option>)}</select>
                    <button className="ingest-submit-btn" disabled={!oppId} onClick={() => act(async () => { await planCreate(oppId); setOppId(""); })}>Add to planner</button>
                    {!opportunities.length && <button className="demo-btn" onClick={() => onNavigate("creator-studio")}>Run an analysis first</button>}
                </div>
            </section>
            <div className="kanban">
                {COLS.map(([key, label], ci) => (
                    <div key={key} className="kanban-col">
                        <h3>{label} <span>{items.filter((i) => i.status === key).length}</span></h3>
                        {items.filter((i) => i.status === key).length === 0 && <div className="empty-state compact"><CircleAlert size={18} /><p>Nothing here yet.</p></div>}
                        {items.filter((i) => i.status === key).map((it) => (
                            <div key={it.id} className="kanban-card">
                                <b>{it.title}</b>
                                <small>{it.topic} · GhostGap {it.ghostgap ?? "n/a"}{it.format ? ` · ${it.format}` : ""}</small>
                                {it.notes && <p className="notes">{it.notes}</p>}
                                {it.video_url && <a href={it.video_url} target="_blank" rel="noreferrer"><ExternalLink size={12} /> published video</a>}
                                {it.status === "published" && <small>Performance tracking started — see Evaluation → Closed-loop validation.</small>}
                                {key === "scripted" && (
                                    <div className="pub-row"><input placeholder="Published video URL" value={pub[it.id] || ""} onChange={(e) => setPub({ ...pub, [it.id]: e.target.value })} />
                                        <button className="mini" disabled={!pub[it.id]} onClick={() => act(() => planPublish(it.id, pub[it.id].trim()))}>Mark published</button></div>)}
                                <div className="card-actions">
                                    {ci > 0 && key !== "published" && <button className="mini" title="Move back" onClick={() => act(() => planUpdate(it.id, { status: COLS[ci - 1][0] }))}><ChevronLeft size={14} /></button>}
                                    {key === "idea" && <button className="mini" title="Move to scripted" onClick={() => act(() => planUpdate(it.id, { status: "scripted" }))}><ChevronRight size={14} /></button>}
                                    <button className="mini" onClick={() => setEdit({ ...it })}>Edit</button>
                                    <button className="mini" onClick={() => onOpenOpp(it.opportunity_id)}>Evidence</button>
                                    <button className="mini danger" onClick={() => act(() => planDelete(it.id))}><Trash2 size={13} /></button>
                                </div>
                            </div>))}
                    </div>))}
            </div>
            {edit && (
                <div className="modal-overlay" onClick={() => setEdit(null)}><div className="modal" onClick={(e) => e.stopPropagation()}>
                    <h2>Edit plan item</h2>
                    <label className="field">Title<input value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></label>
                    <label className="field">Notes<textarea rows={3} value={edit.notes || ""} onChange={(e) => setEdit({ ...edit, notes: e.target.value })} /></label>
                    <label className="field">Script / outline<textarea rows={10} value={edit.script || ""} onChange={(e) => setEdit({ ...edit, script: e.target.value })} /></label>
                    <div className="btn-row"><button className="ingest-submit-btn" onClick={() => act(async () => { await planUpdate(edit.id, { title: edit.title, notes: edit.notes, script: edit.script }); setEdit(null); })}>Save</button>
                        <button className="demo-btn" onClick={() => setEdit(null)}>Cancel</button></div>
                </div></div>)}
        </div>
    );
}
