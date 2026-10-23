import { useState } from "react";
import { Workflow, ShieldCheck, Search, GitBranch, FileText } from "lucide-react";
import { api, setToken } from "../api";
import { WorkflowGraph, Err } from "../ui";

export function Landing() {
  return (
    <div className="relative overflow-hidden">
      <div aria-hidden className="absolute inset-0 pointer-events-none">
        {Array.from({ length: 14 }).map((_, i) => <span key={i} className="particle absolute rounded-full bg-teal2/30"
          style={{ width: 4 + (i % 3) * 3, height: 4 + (i % 3) * 3, left: `${(i * 37) % 100}%`, top: `${(i * 53) % 90}%`, animationDelay: `${i * 0.4}s` }} />)}
      </div>
      <nav className="relative flex justify-between items-center p-6 max-w-6xl mx-auto">
        <span className="flex items-center gap-2 font-bold text-xl"><Workflow className="text-teal2" />FlowSage AI</span>
        <a href="#/auth" className="btn btn-ghost">Sign in</a>
      </nav>
      <section className="relative max-w-4xl mx-auto text-center px-6 py-16">
        <h1 className="text-4xl md:text-6xl font-bold leading-tight">Self-healing workflow <span className="text-teal2">investigations</span></h1>
        <p className="mt-4 text-lg text-gold">Detect the failure. Decide the next step. Explain the evidence. Recover safely.</p>
        <p className="mt-6 text-slate-300">Business workflows fail in ambiguous ways. A timed-out payment might have succeeded, so a blind retry can double-charge a customer.
          FlowSage collects evidence, lets a small decision model choose the next <em>diagnostic</em> action from an explicit allowlist, explains the result, and asks for approval before any (simulated) recovery.</p>
        <a href="#/auth" className="btn btn-primary mt-8 text-base">Launch Demo</a>
        <div className="glass mt-12 p-6"><WorkflowGraph steps={{ order_received: "ok", payment_verification: "failed", order_confirmation: "blocked", dispatch: "pending" }} />
          <p className="text-xs text-slate-400">Illustration of the simulated order workflow (not live data).</p></div>
      </section>
      <section className="relative max-w-6xl mx-auto px-6 grid md:grid-cols-4 gap-4 pb-12">
        {[[Search, "Evidence first", "Collects logs and tool results before deciding."], [GitBranch, "Constrained decisions", "Strands Decider 2B picks from allowlisted actions only."],
          [FileText, "Grounded explanations", "Amazon Bedrock explains using collected evidence."], [ShieldCheck, "Human approval", "High-risk recovery needs explicit approval; all simulated."]]
          .map(([I, t, d]: any) => <div key={t} className="glass p-5"><I className="text-teal2 mb-2" /><h3 className="font-semibold">{t}</h3><p className="text-sm text-slate-300 mt-1">{d}</p></div>)}
      </section>
      <section className="relative max-w-3xl mx-auto px-6 pb-16">
        <div className="glass p-6"><h2 className="font-semibold text-lg mb-2">About the creator</h2>
          <p className="text-sm text-slate-300">Meghana Bobbili — third-year B.Tech (Artificial Intelligence &amp; Data Science), Ramachandra College of Engineering, Eluru, Andhra Pradesh, India. Expected graduation 2028.
            Interests: AI, data science, generative AI, AI agents, prompt engineering, full-stack development.</p>
          <p className="text-sm mt-3 space-x-4"><a className="text-teal2 underline" href="https://github.com/bobbilimeghana2007">GitHub</a><a className="text-teal2 underline" href="https://linkedin.com/in/bobbili-meghana">LinkedIn</a></p></div>
      </section>
    </div>);
}

export function Auth({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true);
    try { const r = await (mode === "login" ? api.login : api.register)(email, pw); setToken(r.token); onDone(); }
    catch (x: any) { setErr(x.message); } finally { setBusy(false); } }
  return (
    <div className="min-h-screen grid place-items-center p-6"><form onSubmit={submit} className="glass p-8 w-full max-w-sm space-y-4">
      <h1 className="text-xl font-bold flex items-center gap-2"><Workflow className="text-teal2" />{mode === "login" ? "Sign in" : "Create account"}</h1>
      <label className="block text-sm">Email<input className="input mt-1" type="email" required value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" /></label>
      <label className="block text-sm">Password (10+ characters)<input className="input mt-1" type="password" required minLength={10} value={pw} onChange={e => setPw(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} /></label>
      <Err msg={err} />
      <button className="btn btn-primary w-full justify-center" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}</button>
      <button type="button" className="text-sm text-teal2 underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
        {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}</button>
      <a href="#/" className="block text-xs text-slate-400">← Back</a></form></div>);
}
