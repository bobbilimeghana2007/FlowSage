import { useEffect, useState } from "react";
import { LayoutDashboard, AlertTriangle, GitBranch, FileBarChart, Settings as Cog, LogOut, Workflow } from "lucide-react";
import { hasToken, setToken } from "./api";
import { Landing, Auth } from "./pages/Public";
import { Overview, Incidents, Trace, Reports, SettingsPage } from "./pages/Workspace";

const NAV = [["overview", "Overview", LayoutDashboard], ["incidents", "Incidents", AlertTriangle], ["trace", "Decision Trace", GitBranch],
  ["reports", "Reports", FileBarChart], ["settings", "Settings", Cog]] as const;

function useRoute() {
  const [h, setH] = useState(location.hash || "#/");
  useEffect(() => { const f = () => setH(location.hash || "#/"); addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  return h.replace("#/", "").split("?");   // [route, query]
}

export default function App() {
  const [route, query] = useRoute();
  const [, force] = useState(0);
  if (route === "" ) return <Landing />;
  if (route === "auth") return <Auth onDone={() => { location.hash = "#/overview"; force(x => x + 1); }} />;
  if (!hasToken()) { location.hash = "#/auth"; return null; }
  const sel = new URLSearchParams(query || "").get("id") || "";
  return (
    <div className="min-h-screen md:flex">
      <aside className="md:w-60 bg-navy-900 border-r border-white/10 p-4 flex md:flex-col gap-1 overflow-x-auto" aria-label="Main navigation">
        <a href="#/" className="flex items-center gap-2 font-bold text-lg mb-0 md:mb-6 mr-4"><Workflow className="text-teal2" /> FlowSage</a>
        {NAV.map(([k, label, Icon]) => (
          <a key={k} href={`#/${k}`} aria-current={route === k ? "page" : undefined}
             className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm whitespace-nowrap ${route === k ? "bg-teal2/15 text-teal2" : "hover:bg-white/5"}`}><Icon size={16} />{label}</a>))}
        <button className="btn btn-ghost mt-auto" onClick={() => { setToken(""); location.hash = "#/"; }}><LogOut size={16} />Sign out</button>
      </aside>
      <main className="flex-1 p-4 md:p-8 max-w-6xl">
        <header className="flex flex-wrap justify-between items-center mb-6 gap-2">
          <p className="text-sm text-slate-400">Workspace · <span className="text-ivory">Personal</span></p>
          <span className="px-3 py-1 rounded-full text-xs bg-gold/20 text-gold">DEMO MODE · all data simulated</span>
        </header>
        {route === "overview" && <Overview />}
        {route === "incidents" && <Incidents selected={sel} />}
        {route === "trace" && <Trace selected={sel} />}
        {route === "reports" && <Reports />}
        {route === "settings" && <SettingsPage />}
      </main>
    </div>);
}
