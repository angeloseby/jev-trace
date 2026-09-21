"use client";
import { useEffect, useState } from "react";
import { fetchProjects, createProject, fetchApiKeys, createApiKey } from "@/lib/api";
import Link from "next/link";

export default function SettingsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [keys, setKeys] = useState<any[]>([]);
  const [newProj, setNewProj] = useState("");
  const [newKeyName, setNewKeyName] = useState("");
  const [lastSecret, setLastSecret] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    const p = await fetchProjects();
    setProjects(p);
    if (p.length && !selected) setSelected(p[0].id);
  }
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (selected) fetchApiKeys(selected).then(setKeys).catch(()=>setKeys([]));
    if (selected) localStorage.setItem("jev_project_id", selected);
  }, [selected]);

  async function handleCreateProject() {
    if (!newProj) return;
    const p = await createProject(newProj);
    setMsg(`Created project ${p.name}`);
    setNewProj("");
    await load();
    setSelected(p.id);
  }
  async function handleCreateKey() {
    if (!selected) return;
    const k: any = await createApiKey(selected, newKeyName || undefined);
    setLastSecret(`Public: ${k.public_key}  Secret: ${k.secret_key}  (save once — secret not shown again)`);
    setNewKeyName("");
    setKeys(await fetchApiKeys(selected));
  }

  return (
    <main className="mx-auto max-w-4xl p-8">
      <Link href="/" className="text-sm text-zinc-500">← Home</Link>
      <h1 className="mt-2 text-2xl font-bold">Settings — Projects & API Keys</h1>
      <p className="text-sm text-zinc-600">Langfuse-like: create project → generate <code>jt_pub_</code>/<code>jt_sec_</code> → use in <code>JevTrace(public_key, secret_key)</code> or <code>POST /api/public/ingestion</code> Basic auth. Default <code>default</code> project pre-seeded.</p>
      {msg && <div className="mt-3 rounded bg-zinc-50 p-2 text-sm">{msg}</div>}
      {lastSecret && <div className="mt-3 rounded bg-amber-50 p-3 text-sm font-mono break-all">{lastSecret}</div>}

      <section className="mt-6 rounded-xl border bg-white p-4">
        <h2 className="font-semibold">Projects</h2>
        <div className="mt-2 flex gap-2">
          <select value={selected} onChange={e=>setSelected(e.target.value)} className="rounded border px-3 py-2 text-sm flex-1">
            {projects.map(p=><option key={p.id} value={p.id}>{p.name} ({p.id.slice(0,8)})</option>)}
            {projects.length===0 && <option>No projects</option>}
          </select>
        </div>
        <div className="mt-3 flex gap-2">
          <input value={newProj} onChange={e=>setNewProj(e.target.value)} placeholder="new project name" className="flex-1 rounded border px-3 py-2 text-sm" />
          <button onClick={handleCreateProject} className="rounded bg-zinc-900 px-4 py-2 text-sm text-white">Create project</button>
        </div>
      </section>

      <section className="mt-6 rounded-xl border bg-white p-4">
        <h2 className="font-semibold">API Keys — project {selected?.slice(0,8) || "—"}</h2>
        <p className="text-xs text-zinc-500">Use as <code>Authorization: Basic base64(public:secret)</code> or <code>X-Api-Key: public</code> + secret, or in tracer <code>JevTrace(public_key, secret_key)</code>.</p>
        <ul className="mt-3 space-y-2 text-sm">
          {keys.map(k=><li key={k.id} className="flex justify-between rounded border px-3 py-2"><span className="font-mono text-xs">{k.public_key} — {k.name||"unnamed"}</span><span className="text-xs text-zinc-500">{new Date(k.created_at).toLocaleString()}</span></li>)}
          {keys.length===0 && <li className="text-sm text-zinc-500">No keys — create one below. Default project works with no key for local demo.</li>}
        </ul>
        <div className="mt-3 flex gap-2">
          <input value={newKeyName} onChange={e=>setNewKeyName(e.target.value)} placeholder="key name (optional)" className="flex-1 rounded border px-3 py-2 text-sm" />
          <button onClick={handleCreateKey} className="rounded bg-zinc-900 px-4 py-2 text-sm text-white">Generate jt_pub_/jt_sec_</button>
        </div>
        <pre className="mt-4 rounded bg-zinc-900 p-3 text-xs text-zinc-100">{`from jev_trace import JevTrace
tracer = JevTrace(host="http://localhost:8000", public_key="jt_pub_...", secret_key="jt_sec_...")
with tracer.span("retriever", inputs={"query": q}):
    docs = retriever(q)
# or @tracer.observe
@tracer.observe(component="planner")
def my_planner(x): return plan(x)
tracer.flush()
`}</pre>
      </section>

      <section className="mt-6 rounded-xl border bg-white p-4">
        <h2 className="font-semibold">Langfuse-like env</h2>
        <pre className="mt-2 rounded bg-zinc-900 p-3 text-xs text-zinc-100">{`JEVTRACE_HOST=http://localhost:8000
JEVTRACE_PUBLIC_KEY=jt_pub_...
JEVTRACE_SECRET_KEY=jt_sec_...
# or OTEL: OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`}</pre>
        <p className="mt-2 text-xs text-zinc-500">OTel collector at :4318 → <code>POST /api/v1/otlp/traces</code> auto-maps <code>llm→generator</code> etc. See <code>docs/integration.md</code>.</p>
      </section>
    </main>
  );
}
