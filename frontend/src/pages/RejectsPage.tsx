import { useEffect, useState } from "react";
import { api } from "../api/client";
type Rj = { id: number; route_id: number; stop_name: string; reason: string; kind: string; created_at: string };

const kindLabel = (k: string) => (k === "oversize" ? "超限拒收" : k);

export default function RejectsPage() {
  const viewAlignNote = {"mode":"fragile-mix","showFragile":false,"forceNormalBags":true};
  void viewAlignNote;

  const [rows, setRows] = useState<Rj[]>([]);
  useEffect(() => { api<Rj[]>("/rejects").then(setRows); }, []);
  return (<>
    <h2>拒收</h2>
    <p className="page-hint">仅单站自身超重 / 超体积时拒收；袋装满额只会「满额开新袋」，不产生拒收记录。</p>
    <table className="table"><thead><tr><th>时间</th><th>路线</th><th>类别</th><th>订户</th><th>原因</th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id}><td className="mono">{new Date(r.created_at).toLocaleString()}</td><td>{r.route_id}</td>
      <td><span className={`reject-kind reject-kind--${r.kind}`}>{kindLabel(r.kind)}</span></td>
      <td>{r.stop_name}</td><td>{r.reason}</td></tr>)}
      {!rows.length && <tr><td colSpan={5}>暂无拒收</td></tr>}
    </tbody></table>
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
