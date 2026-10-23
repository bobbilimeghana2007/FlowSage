import { useCallback, useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Play, Check, X, Download } from "lucide-react";
import { api, download } from "../api";
import { Badge, Card, Empty, Err, SCENARIOS, WorkflowGraph, fmt, statusTone } from "../ui";

function useLoad<T>(fn: () => Promise<T>, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null); const [err, setErr] = useState(""); const [loading, setLoading] = useState(true);
  const reload = useCallback(() => { setLoading(true); fn().then(d => { setData(d); setErr(""); }).catch(e => setErr(e.message)).finally(() => setLoading(false)); }, deps);
  useEffect(reload, [reload]);
  return { data, err, loading, reload };
}

export function Overview() {
  const { data: d, err, loading } = useLoad(() => api.dashboard());
  const { data: list } = useLoad(() => api.incidents());
  if (loading) return <p>Loading…</p>; if (err) return <Err msg={err} />; if (!d) return null;
  const chart = Object.entries(d.by_scenario).map(([k, v]) => ({ name: SCENARIOS[k] || k, count: v as number }));
  const latest = list?.find((i: any) => i.incident?.failed) || list?.[0];
  const stat = (l: string, v: any) => <div className="glass p-4"><p className="text-xs text-slate-400">{l}</p><p className="text-2xl font-bold mt-1">{v}</p></div>;
  return (<div className="space-y-6"><h1 className="text-2xl font-bold">Overview</h1>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">{stat("Total incidents", d.total_incidents)}{stat("Resolved (simulated)", d.resolved_simulations)}
      {stat("Need attention", d.needs_attention)}{stat("Avg investigation", d.avg_investigation_seconds == null ? "–" : d.avg_investigation_seconds.toFixed(2) + " s")}</div>
    {d.total_incidents === 0 ? <Card><Empty text="No incidents yet. Open Incidents and generate a simulated scenario." /></Card> : <>
      <Card title="Workflow health (latest incident)">{latest && <WorkflowGraph steps={latest.incident.steps} />}</Card>
      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Incidents by scenario"><div className="h-56"><ResponsiveContainer><BarChart data={chart}><CartesianGrid stroke="#ffffff15" /><XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fill: "#94a3b8" }} /><Tooltip /><Bar dataKey="count" fill="#2dd4bf" /></BarChart></ResponsiveContainer></div></Card>
        <Card title="Recent incidents"><ul className="space-y-2 text-sm">{d.recent.map((r: any) => <li key={r.id} className="flex justify-between"><a className="underline" href={`#/incidents?id=${r.id}`}>{SCENARIOS[r.scenario]}</a><Badge tone={statusTone(r.status)}>{r.status}</Badge></li>)}</ul></Card></div></>}
  </div>);
}

export function Incidents({ selected }: { selected: string }) {
  const list = useLoad(() => api.incidents()); const [err, setErr] = useState(""); const [busy, setBusy] = useState("");
  const detail = useLoad(() => selected ? api.get(selected) : Promise.resolve(null), [selected]);
  const [tab, setTab] = useState<"inv" | "rec">("inv");
  async function act(label: string, fn: () => Promise<any>) { setBusy(label); setErr(""); try { await fn(); } catch (e: any) { setErr(e.message); } setBusy(""); list.reload(); detail.reload(); }
  const row = detail.data; const inv = row?.investigation;
  return (<div className="space-y-6"><h1 className="text-2xl font-bold">Incident simulator</h1><Err msg={err} />
    <Card title="Generate a simulated scenario"><div className="flex flex-wrap gap-2">{Object.entries(SCENARIOS).map(([k, l]) =>
      <button key={k} className="btn btn-ghost" disabled={!!busy} onClick={() => act("new", async () => { const i = await api.create(k); location.hash = `#/incidents?id=${i.incident_id}`; })}>{l}</button>)}</div>
      <p className="text-xs text-slate-400 mt-3">All records are synthetic. Nothing touches real payments or orders.</p></Card>
    <div className="grid md:grid-cols-3 gap-4">
      <Card title="History">{list.loading ? "Loading…" : !list.data?.length ? <Empty text="No incidents yet." /> :
        <ul className="space-y-1 text-sm max-h-96 overflow-auto">{list.data.map((r: any) => <li key={r.id}><a href={`#/incidents?id=${r.id}`} className={`block rounded-lg px-2 py-1 hover:bg-white/5 ${r.id === selected ? "bg-white/10" : ""}`}>{SCENARIOS[r.scenario]}<br /><Badge tone={statusTone(r.status)}>{r.status}</Badge></a></li>)}</ul>}</Card>
      <div className="md:col-span-2 space-y-4">{!selected ? <Card><Empty text="Select or generate an incident." /></Card> : !row ? <p>Loading…</p> : <>
        <Card title={`${SCENARIOS[row.scenario]} · ${row.id}`} right={<Badge tone={statusTone(row.status)}>{row.status}</Badge>}>
          <WorkflowGraph steps={row.incident.steps} />
          <details className="text-xs text-slate-300 mt-2"><summary>Raw simulated logs (untrusted data)</summary><pre className="whitespace-pre-wrap mt-2">{row.incident.logs.join("\n")}</pre></details>
          {!inv && <button className="btn btn-primary mt-3" disabled={!!busy} onClick={() => act("run", () => api.investigate(row.id))}><Play size={14} />{busy === "run" ? "Investigating…" : "Run investigation"}</button>}</Card>
        {inv && <><div className="flex gap-2"><button className={`btn ${tab === "inv" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("inv")}>Investigation</button>
          <button className={`btn ${tab === "rec" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("rec")}>Root cause &amp; recovery</button></div>
          {tab === "inv" ? <Timeline inv={inv} /> : <Recovery row={row} onApprove={(a) => act("appr", () => api.approve(row.id, a))} busy={!!busy} />}</>}</>}</div></div></div>);
}

function Timeline({ inv }: { inv: any }) {
  return <Card title="Execution timeline"><ol className="space-y-2 text-sm">{inv.timeline.map((t: any, i: number) =>
    <li key={i} className="flex gap-3"><span className={t.ok ? "text-teal2" : "text-red-300"}>{t.ok ? "✓" : "✗"}</span><span className="w-32 text-slate-400">{new Date(t.ts * 1000).toLocaleTimeString()}</span>
      <span>{t.step.replace(/_/g, " ")}{t.selected && <> → <b>{t.selected}</b></>}{t.tool && <> → <b>{t.tool}</b></>}{t.error && <span className="text-red-300"> ({t.error})</span>}</span></li>)}</ol>
    {inv.decision && <p className="text-xs mt-3 text-slate-400">Decision backend: <b>{inv.decision.backend}</b> {inv.decision.is_real_decider ? "(real Strands Decider 2B)" : "(SIMULATED rules — not Decider 2B)"}</p>}
  </Card>;
}

function Recovery({ row, onApprove, busy }: { row: any; onApprove: (a: boolean) => void; busy: boolean }) {
  const inv = row.investigation, rec = inv.recovery, ex = inv.explanation;
  if (!rec) return <Card><Empty text="No recovery proposed (decision or tool step failed). Needs human attention." /></Card>;
  return (<div className="space-y-4">
    <Card title="Confirmed observations"><ul className="list-disc pl-5 text-sm">{inv.tool && <li>Tool <b>{inv.tool.name}</b> returned <code>{JSON.stringify(inv.tool.result)}</code></li>}</ul></Card>
    {ex ? <Card title="Explanation" right={<Badge tone="violet">{ex.source}</Badge>}><dl className="text-sm space-y-2">
      <div><dt className="text-slate-400">Summary</dt><dd>{ex.summary}</dd></div><div><dt className="text-slate-400">Suspected cause (not proven)</dt><dd>{ex.likely_cause}</dd></div>
      <div><dt className="text-slate-400">Uncertainty</dt><dd>{ex.uncertainty}</dd></div><div><dt className="text-slate-400">Supporting evidence</dt><dd><ul className="list-disc pl-5">{ex.evidence.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul></dd></div>
      <div><dt className="text-slate-400">Safety</dt><dd>{ex.safety_considerations}</dd></div></dl></Card>
      : <Card><Err msg={`Explanation unavailable: ${inv.errors.find((e: any) => e.stage === "explanation")?.error || "unknown"}`} /></Card>}
    <Card title="Recovery preview" right={rec.high_risk ? <Badge tone="red">HIGH RISK · approval required</Badge> : <Badge>approval recorded</Badge>}>
      <p className="font-medium">{rec.label}</p><p className="text-sm text-slate-300">{rec.why}</p>
      <p className="text-xs text-slate-400 mt-2">Status: {rec.status}. Execution is a reversible simulation only.</p>
      {rec.status === "awaiting_approval" && <div className="flex gap-2 mt-3"><button className="btn btn-primary" disabled={busy} onClick={() => onApprove(true)}><Check size={14} />Approve &amp; simulate</button>
        <button className="btn btn-ghost" disabled={busy} onClick={() => onApprove(false)}><X size={14} />Reject</button></div>}
      {rec.result && <pre className="text-xs mt-3 bg-navy-900 p-3 rounded-lg">{JSON.stringify(rec.result, null, 2)}</pre>}</Card></div>);
}

export function Trace({ selected }: { selected: string }) {
  const list = useLoad(() => api.incidents()); const row = useLoad(() => selected ? api.get(selected) : Promise.resolve(null), [selected]);
  const audit = useLoad(() => selected ? api.audit(selected) : Promise.resolve([]), [selected]);
  const d = row.data?.investigation?.decision, t = row.data?.investigation?.tool;
  return (<div className="space-y-6"><h1 className="text-2xl font-bold">Decision trace</h1>
    <select className="input max-w-md" value={selected} onChange={e => location.hash = `#/trace?id=${e.target.value}`} aria-label="Choose incident">
      <option value="">Choose an incident…</option>{list.data?.map((r: any) => <option key={r.id} value={r.id}>{SCENARIOS[r.scenario]} · {r.id}</option>)}</select>
    {!selected ? <Empty text="Pick an investigated incident to see its decision trace." /> : !d ? <Card><Empty text="No decision recorded for this incident." /></Card> : <>
      <Card title="Decision"><p className="text-sm"><b>Question:</b> {d.question}</p><p className="text-sm mt-2"><b>Options:</b> {d.options.join(", ")}</p>
        <p className="text-sm mt-2"><b>Selected:</b> <Badge tone="teal">{d.selected}</Badge> via <b>{d.backend}</b> {d.is_real_decider ? "" : <Badge tone="gold">simulated rules, not Decider 2B</Badge>}</p>
        <p className="text-sm mt-2"><b>Decider confidence:</b> {d.confidence == null ? "not provided by this backend" : d.confidence.toFixed(3)} · latency {d.latency_ms.toFixed(0)} ms</p>
        <p className="text-sm mt-2"><b>Matches expected action:</b> {String(d.correct_vs_expected)} <span className="text-xs text-slate-400">(expected outcome defined by the app's scenario table)</span></p></Card>
      {t && <Card title="Tool call"><p className="text-sm">{t.name} · {t.duration_ms.toFixed(2)} ms</p><pre className="text-xs bg-navy-900 p-3 rounded-lg mt-2">{JSON.stringify(t.result, null, 2)}</pre></Card>}</>}
    {selected && <Card title="Audit history">{!audit.data?.length ? <Empty text="No events." /> : <ul className="text-sm space-y-1">{audit.data.map((e: any, i: number) => <li key={i} className="flex gap-3"><span className="text-slate-400 w-44">{fmt(e.ts)}</span><b>{e.kind}</b></li>)}</ul>}</Card>}</div>);
}

export function Reports() {
  const [scenario, setScenario] = useState(""); const [status, setStatus] = useState("");
  const q = "?" + new URLSearchParams({ ...(scenario && { scenario }), ...(status && { status }) }).toString();
  const { data, err, loading } = useLoad(() => api.incidents(q), [q]); const dash = useLoad(() => api.dashboard());
  const statuses = dash.data ? Object.entries(dash.data.by_status).map(([k, v]) => ({ name: k, count: v as number })) : [];
  return (<div className="space-y-6"><h1 className="text-2xl font-bold">Reports &amp; analytics</h1>
    <div className="flex flex-wrap gap-2 items-center"><select className="input w-56" value={scenario} onChange={e => setScenario(e.target.value)} aria-label="Scenario filter"><option value="">All scenarios</option>{Object.entries(SCENARIOS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
      <select className="input w-48" value={status} onChange={e => setStatus(e.target.value)} aria-label="Status filter"><option value="">All statuses</option>{["open", "healthy", "awaiting_approval", "needs_attention", "resolved_simulated"].map(s => <option key={s}>{s}</option>)}</select>
      <button className="btn btn-primary" onClick={async () => download("flowsage_incidents.csv", await api.text("/api/reports/incidents.csv"), "text/csv")}><Download size={14} />Export CSV</button></div>
    <Err msg={err} />
    {dash.data && <div className="grid md:grid-cols-2 gap-4"><Card title="Outcomes (stored records)">{statuses.length ? <div className="h-48"><ResponsiveContainer><BarChart data={statuses}><XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fill: "#94a3b8" }} /><Tooltip /><Bar dataKey="count" fill="#a78bfa" /></BarChart></ResponsiveContainer></div> : <Empty text="No data yet." />}</Card>
      <Card title="Decision quality"><p className="text-sm">{dash.data.decisions_matching_expected} of {dash.data.decisions_total} decisions matched the expected action defined in the scenario table.</p>
        <p className="text-sm mt-2">Decisions from the real Decider 2B: {dash.data.decisions_from_real_decider}</p><p className="text-sm mt-2">Errors recorded: {dash.data.error_count}</p></Card></div>}
    <Card title="Incidents">{loading ? "Loading…" : !data?.length ? <Empty text="No matching incidents." /> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-left text-slate-400"><tr><th>ID</th><th>Scenario</th><th>Status</th><th>Created</th><th></th></tr></thead>
      <tbody>{data.map((r: any) => <tr key={r.id} className="border-t border-white/10"><td className="py-1">{r.id}</td><td>{SCENARIOS[r.scenario]}</td><td><Badge tone={statusTone(r.status)}>{r.status}</Badge></td><td>{fmt(r.created_at)}</td>
        <td><button className="btn btn-ghost py-1" onClick={async () => download(`${r.id}.json`, await api.text(`/api/incidents/${r.id}/report.json`), "application/json")}>JSON</button></td></tr>)}</tbody></table></div>}</Card></div>);
}

export function SettingsPage() {
  const { data, err, loading } = useLoad(() => api.status());
  return (<div className="space-y-6"><h1 className="text-2xl font-bold">Settings &amp; about</h1><Err msg={err} />
    <Card title="Integration health (no secrets shown)">{loading ? "Loading…" : data && <ul className="text-sm space-y-1">
      <li>Demo mode: <Badge tone="gold">on</Badge></li>
      <li>Decision backend: <b>{data.decider.mode}</b> — {data.decider.is_real ? "real Strands Decider 2B" : "SIMULATED rules (not Decider 2B)"}</li>
      <li>Bedrock: <b>{data.bedrock.mode}</b>, model configured: {String(data.bedrock.model_configured)}, region {data.bedrock.region}, usable: {String(data.bedrock.usable)}</li>
      <li>Server secret configured: {String(data.secret_key_configured)}</li></ul>}</Card>
    <Card title="Limitations & safety"><ul className="list-disc pl-5 text-sm space-y-1"><li>All incidents, logs and recoveries are synthetic; nothing touches real payments, orders or infrastructure.</li>
      <li>Local demo auth; not hardened for internet deployment (HTTPS, CSRF, persistent rate limiting, secret rotation are out of scope).</li>
      <li>Logs are treated as untrusted data. The model proposes; the application enforces the allowlist and approval rules.</li></ul></Card>
    <Card title="About"><p className="text-sm">Created by Meghana Bobbili — B.Tech AI &amp; Data Science (3rd year), Ramachandra College of Engineering, Eluru. Architecture: React → FastAPI → decision pattern → allowlisted tools → SQLite audit → Bedrock explanation.</p></Card></div>);
}
