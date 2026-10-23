import { ReactNode } from "react";
export const SCENARIOS: Record<string, string> = {
  payment_timeout: "Payment verification timeout", dependency_unavailable: "Dependency unavailable", api_rate_limit: "API rate limit",
  invalid_configuration: "Invalid configuration", scheduled_failure: "Scheduled workflow failure", success: "Successful workflow (comparison)" };
export const STEPS = ["order_received", "payment_verification", "order_confirmation", "dispatch"];
const COLORS: Record<string, string> = { ok: "#2dd4bf", failed: "#f87171", blocked: "#e7c26a", pending: "#64748b" };

export function WorkflowGraph({ steps }: { steps: Record<string, string> }) {
  return (<svg viewBox="0 0 640 110" className="w-full" role="img" aria-label="Workflow steps and their states">
    {STEPS.map((s, i) => { const st = steps[s] || "pending", x = 20 + i * 160; return (<g key={s}>
      {i > 0 && <line x1={x - 60} y1="45" x2={x} y2="45" stroke="#475569" strokeWidth="2" strokeDasharray="4 4" />}
      <circle cx={x + 40} cy="45" r="26" fill="none" stroke={COLORS[st]} strokeWidth="3" />
      <circle cx={x + 40} cy="45" r="8" fill={COLORS[st]} />
      <text x={x + 40} y="95" textAnchor="middle" fontSize="11" fill="#e2e8f0">{s.replace("_", " ")}</text>
      <text x={x + 40} y="10" textAnchor="middle" fontSize="10" fill={COLORS[st]}>{st}</text></g>); })}</svg>);
}
export const Badge = ({ children, tone = "slate" }: { children: ReactNode; tone?: string }) => {
  const t: Record<string, string> = { slate: "bg-white/10", teal: "bg-teal2/20 text-teal2", gold: "bg-gold/20 text-gold", red: "bg-red-400/20 text-red-300", violet: "bg-violet2/20 text-violet2" };
  return <span className={`px-2 py-0.5 rounded-full text-xs ${t[tone]}`}>{children}</span>; };
export const Card = ({ title, children, right }: { title?: string; children: ReactNode; right?: ReactNode }) => (
  <section className="glass p-5">{(title || right) && <div className="flex justify-between items-center mb-3"><h3 className="font-semibold">{title}</h3>{right}</div>}{children}</section>);
export const Empty = ({ text }: { text: string }) => <p className="text-sm text-slate-400 py-6 text-center">{text}</p>;
export const Err = ({ msg }: { msg: string }) => msg ? <p role="alert" className="text-sm text-red-300 bg-red-400/10 rounded-lg px-3 py-2">{msg}</p> : null;
export const statusTone = (s: string) => ({ resolved_simulated: "teal", healthy: "teal", awaiting_approval: "gold", needs_attention: "red" } as any)[s] || "slate";
export const fmt = (ts?: number) => ts ? new Date(ts * 1000).toLocaleString() : "-";
