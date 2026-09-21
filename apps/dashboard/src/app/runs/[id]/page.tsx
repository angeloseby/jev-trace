"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchRun, fetchSteps, fetchAttribution, fetchGraph, fetchRecommendations, analyzeRun, completeRun } from "@/lib/api";

export default function RunDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id as string;
  const [run, setRun] = useState<any>(null);
  const [steps, setSteps] = useState<any>(null);
  const [attr, setAttr] = useState<any>(null);
  const [graph, setGraph] = useState<any>(null);
  const [recs, setRecs] = useState<any>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      setErr(null);
      const [r, s] = await Promise.all([fetchRun(id), fetchSteps(id)]);
      setRun(r); setSteps(s);
      try { setAttr(await fetchAttribution(id)); } catch { setAttr(null); }
      try { setGraph(await fetchGraph(id)); } catch { setGraph(null); }
      try { setRecs(await fetchRecommendations(id)); } catch { setRecs(null); }
    } catch (e:any){ setErr(String(e.message||e)); }
  }
  useEffect(()=>{ load(); },[id]);

  async function doComplete(status:string){
    try{ await completeRun(id, status); setMsg(`Run ${status}`); await load(); } catch(e:any){ setErr(String(e.message||e)); }
  }
  async function doAnalyze(){
    try{ setMsg("Analyzing via Jev (parallel Choice/Score/Noul)…"); await analyzeRun(id); setMsg("Analyze accepted (202) — polling…"); setTimeout(load, 1500); } catch(e:any){ setErr(String(e.message||e)); }
  }

  if(!run) return <main className="mx-auto max-w-5xl p-8"><Link href="/runs" className="text-sm text-zinc-500">← Runs</Link><p className="mt-4 text-sm text-zinc-500">{err||"Loading…"}</p></main>;

  return (
    <main className="mx-auto max-w-5xl p-8">
      <Link href="/runs" className="text-sm text-zinc-500">← Runs</Link>
      <div className="mt-2 flex items-center gap-3"><h1 className="text-xl font-bold font-mono">{id.slice(0,8)}</h1><span className={`rounded px-2 py-1 text-xs ${run.status==="failed"?"bg-red-100 text-red-700":"bg-zinc-100"}`}>{run.status}</span></div>
      <p className="text-sm text-zinc-600">{run.task_name} • {run.total_steps} steps • {new Date(run.started_at).toLocaleString()}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={()=>doComplete("completed")} className="rounded border px-3 py-1.5 text-sm">Complete</button>
        <button onClick={()=>doComplete("failed")} className="rounded border px-3 py-1.5 text-sm">Mark failed</button>
        <button onClick={doAnalyze} className="rounded bg-zinc-900 px-3 py-1.5 text-sm text-white">POST /analyze (Jev)</button>
        <button onClick={load} className="rounded border px-3 py-1.5 text-sm">Refresh</button>
      </div>
      {msg && <div className="mt-3 rounded bg-zinc-50 p-2 text-sm">{msg}</div>}
      {err && <div className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{err}</div>}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-4">
          <h2 className="font-semibold">Trace Explorer — {steps?.items?.length||0} steps</h2>
          <p className="text-xs text-zinc-500">`GET /runs/{id}/steps` • cursor pagination • input/output/latency</p>
          <div className="mt-3 max-h-96 overflow-auto rounded border">
            <table className="w-full text-xs"><thead className="bg-zinc-50"><tr><th className="px-2 py-1 text-left">#</th><th className="px-2 py-1 text-left">Component</th><th className="px-2 py-1">Status</th><th className="px-2 py-1">Latency</th></tr></thead>
            <tbody>
              {steps?.items?.map((s:any)=>(
                <tr key={s.id} className="border-t"><td className="px-2 py-1">{s.step_number}</td><td className="px-2 py-1">{s.component}</td><td className="px-2 py-1 text-center"><span className={s.status==="failed"?"text-red-600":"text-zinc-600"}>{s.status}</span></td><td className="px-2 py-1 text-center">{s.latency_ms??"—"} ms</td></tr>
              ))}
              {!steps?.items?.length && <tr><td colSpan={4} className="px-2 py-6 text-center text-zinc-500">No steps — `POST /runs/{id}/steps`</td></tr>}
            </tbody></table>
          </div>
          <details className="mt-2"><summary className="cursor-pointer text-xs text-zinc-600">Raw step payloads</summary><pre className="mt-1 max-h-40 overflow-auto rounded bg-zinc-900 p-2 text-xs text-zinc-100">{JSON.stringify(steps?.items?.slice(0,2), null, 2)}</pre></details>
        </section>

        <section className="rounded-xl border bg-white p-4">
          <h2 className="font-semibold">Attribution</h2>
          <p className="text-xs text-zinc-500">`GET /runs/{id}/attribution` — Jev Choice/Score/Noul</p>
          {!attr ? <p className="mt-3 text-sm text-zinc-500">No attribution — run `POST /analyze` (requires `JEV_API_KEY`, `POST /v1/systemone` with parallel questions)</p> :
            <div className="mt-3 space-y-2 text-sm">
              <div><span className="text-zinc-500">Responsible:</span> <b>{attr.responsible_component}</b> <span className="text-zinc-500">({Math.round(attr.component_confidence*100)}%)</span></div>
              <div><span className="text-zinc-500">Failure step:</span> {attr.failure_step ?? "—"}</div>
              <div><span className="text-zinc-500">Category:</span> {attr.failure_category} ({Math.round(attr.category_confidence*100)}%)</div>
              <div><span className="text-zinc-500">Severity:</span> {attr.severity} <span className="text-zinc-500">({attr.severity<1?"Low":attr.severity<2?"Medium":attr.severity<3?"High":"Critical"})</span></div>
            </div>
          }
          {recs?.recommendations?.length>0 && <div className="mt-4"><h3 className="text-sm font-semibold">Recommendations — `POST /recommendations` (Jev repair Choice)</h3><ul className="mt-1 text-sm">{recs.recommendations.map((r:any)=><li key={r.recommendation}>• {r.recommendation} ({Math.round(r.confidence*100)}%)</li>)}</ul></div>}
          {graph?.nodes?.length>0 && <div className="mt-4"><h3 className="text-sm font-semibold">Causal graph — `GET /graph`</h3><div className="mt-1 flex flex-wrap gap-1">{graph.nodes.map((n:any)=><span key={n.id} className="rounded bg-zinc-900 px-2 py-1 text-xs text-white">{n.id} {n.weight.toFixed(2)}</span>)}</div><pre className="mt-2 max-h-28 overflow-auto rounded bg-zinc-900 p-2 text-xs text-zinc-100">{JSON.stringify(graph,null,2)}</pre></div>}
        </section>
      </div>
    </main>
  );
}
