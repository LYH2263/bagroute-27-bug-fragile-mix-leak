import { useEffect, useState } from "react";
import { api } from "../api/client";
type S = { id: number; route_id: number; seq: number; name: string; weight_kg: number; volume_l: number; fragile: boolean };
type R = { id: number; name: string };
export default function StopsPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [rows, setRows] = useState<S[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  useEffect(() => {
    if (rid === "") return;
    api<S[]>(`/stops?route_id=${rid}`).then(setRows);
  }, [rid]);
  async function toggle(s: S) {
    setBusyId(s.id);
    const next = !s.fragile;
    // optimistic update, then persist
    setRows(rs => rs.map(r => (r.id === s.id ? { ...r, fragile: next } : r)));
    try {
      const saved = await api<S>(`/stops/${s.id}`, { method: "PATCH", body: JSON.stringify({ fragile: next }) });
      setRows(rs => rs.map(r => (r.id === s.id ? saved : r)));
    } catch {
      setRows(rs => rs.map(r => (r.id === s.id ? { ...r, fragile: !next } : r)));
    } finally {
      setBusyId(null);
    }
  }
  return (<>
    <h2>订户点</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
    </div>
    <div className="route-strip">
      {rows.map(s => (
        <div className={`stop-chip${s.fragile ? " stop-chip--fragile" : ""}`} key={s.id}>
          <span className="seq">#{s.seq}</span>
          <strong>{s.name}</strong>
          <span className="mono">{s.weight_kg}kg · {s.volume_l}L</span>
          {s.fragile && <span className="fragile-tag">易碎</span>}
          <label className="fragile-toggle">
            <input type="checkbox" checked={s.fragile} disabled={busyId === s.id} onChange={() => toggle(s)} />
            易碎
          </label>
        </div>
      ))}
    </div>
  </>);
}
