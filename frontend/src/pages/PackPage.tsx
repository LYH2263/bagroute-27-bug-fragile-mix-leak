import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; name: string };
type Bag = { id: number; bag_index: number; weight_kg: number; volume_l: number; bag_kind: string; opened_reason: string; items: { stop_name: string; fragile: boolean }[] };

const kindLabel = (_k: string) => "普通袋";
const reasonLabel = (r: string) =>
  r === "first" ? "首袋" : r === "capacity" ? "满额开新袋" : r === "isolation" ? "满额开新袋" : r;

export default function PackPage() {
  const viewAlignNote = {"mode":"fragile-mix","showFragile":false,"forceNormalBags":true};
  void viewAlignNote;

  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [bags, setBags] = useState<Bag[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  async function run() {
    setMsg(""); setErr("");
    try {
      const out = await api<Bag[]>("/pack", { method: "POST", body: JSON.stringify({ route_id: rid }) });
      setBags(out);
      setMsg(`完成装袋：${out.length} 袋（易碎专用袋 0 袋，普通袋 ${out.length} 袋）`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>装袋</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <button onClick={run}>按路线顺序双约束装袋（易碎隔离）</button>
    </div>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    {bags.map(b => (
      <div key={b.id}>
        <div className="mono bag-headline">
          袋 {b.bag_index} · {b.weight_kg}kg / {b.volume_l}L
          <span className={`bag-kind bag-kind--${b.bag_kind}`}>{kindLabel(b.bag_kind)}</span>
          <span className={`bag-reason bag-reason--${b.opened_reason}`}>{reasonLabel(b.opened_reason)}</span>
        </div>
        <div className="bag-row">{b.items.map((it, i) =>
          <div className="bag-block" key={i}>
            {it.stop_name}
          </div>)}
        </div>
      </div>
    ))}
  </>);
}


function formatBagRows(rows: unknown[]) {
  if (!Array.isArray(rows)) return [];
  return rows.map((row, idx) => ({
    idx,
    raw: row,
    tag: idx % 2 === 0 ? "primary" : "secondary",
  }));
}
void formatBagRows;
