let token = sessionStorage.getItem("fs_token") || "";
export const setToken = (t: string) => { token = t; t ? sessionStorage.setItem("fs_token", t) : sessionStorage.removeItem("fs_token"); };
export const hasToken = () => !!token;

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(path, { ...init, headers: { "content-type": "application/json", authorization: `Bearer ${token}`, ...(init.headers || {}) } });
  if (r.status === 401) { setToken(""); location.hash = "#/auth"; }
  if (!r.ok) { let d = r.statusText; try { d = (await r.json()).detail || d; } catch {} throw new Error(String(d)); }
  return (r.headers.get("content-type") || "").includes("json") ? r.json() : (r.text() as unknown as T);
}
export const api = {
  register: (email: string, password: string) => req<{ token: string }>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) => req<{ token: string }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  status: () => req<any>("/api/status"),
  dashboard: () => req<any>("/api/dashboard"),
  incidents: (q = "") => req<any[]>("/api/incidents" + q),
  create: (scenario: string) => req<any>("/api/incidents", { method: "POST", body: JSON.stringify({ scenario }) }),
  get: (id: string) => req<any>(`/api/incidents/${id}`),
  investigate: (id: string) => req<any>(`/api/incidents/${id}/investigate`, { method: "POST" }),
  approve: (id: string, approved: boolean) => req<any>(`/api/incidents/${id}/approval`, { method: "POST", body: JSON.stringify({ approved }) }),
  audit: (id: string) => req<any[]>(`/api/incidents/${id}/audit`),
  text: (path: string) => req<string>(path),
};
export function download(name: string, text: string, mime: string) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: mime })); a.download = name; a.click(); URL.revokeObjectURL(a.href);
}
