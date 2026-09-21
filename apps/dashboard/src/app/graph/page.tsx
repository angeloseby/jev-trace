"use client";
import Link from "next/link";
import { useState } from "react";
import { fetchGraph } from "@/lib/api";

export default function GraphPage(){
  const [runId,setRunId]=useState("");
  const [graph,setGraph]=useState<any>(null);
  const [err,setErr]=useState<string|null>(null);
  async function load(){
    try{ setErr(null); setGraph(await fetchGraph(runId)); } catch(e:any){ setErr(String(e.message||e)); setGraph(null); }
  }
  return (
    <main className="mx-auto max-w-4xl p-8">
      <Link href="/" className="text-sm text-zinc-500">← Home</Link>
      <h1 className="mt-2 text-2xl font-bold">Attribution Graph</h1>
      <p className="text-sm text-zinc-600">`GET /api/v1/runs/{"{id}"}/graph` • per-component weights from Jev Noul — the differentiator</p>
      <div className="mt-4 flex gap-2">
        <input value={runId} onChange={e=>setRunId(e.target.value)} placeholder="run UUID" className="flex-1 rounded border px-3 py-2 text-sm font-mono" />
        <button onClick={load} className="rounded bg-zinc-900 px-4 py-2 text-sm text-white">Load graph</button>
      </div>
      {err && <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{err}</div>}
      {graph && (
        <div className="mt-6 rounded-xl border bg-white p-6">
          <h2 className="font-semibold">Nodes (weight 0→1)</h2>
          <div className="mt-3 space-y-2">
            {graph.nodes?.sort((a:any,b:any)=>b.weight-a.weight).map((n:any)=>(
              <div key={n.id} className="flex items-center gap-3">
                <span className="w-28 text-sm">{n.id}</span>
                <div className="h-3 flex-1 rounded bg-zinc-100"><div className="h-3 rounded" style={{width:`${n.weight*100}%`, background: n.weight>0.7 ? "#dc2626" : n.weight>0.3 ? "#f59e0b" : "#18181b"}}/></div>
                <span className="w-12 text-right text-sm">{n.weight.toFixed(2)}</span>
              </div>
            ))}
          </div>
          <details className="mt-4"><summary className="cursor-pointer text-sm text-zinc-600">Edges (linear order)</summary><pre className="mt-2 rounded bg-zinc-900 p-3 text-xs text-zinc-100">{JSON.stringify(graph.edges, null,2)}</pre></details>
          <pre className="mt-4 rounded bg-zinc-900 p-3 text-xs text-zinc-100">{JSON.stringify(graph,null,2)}</pre>
        </div>
      )}
      {!graph && <p className="mt-6 text-sm text-zinc-500">Paste a run ID from <Link href="/runs" className="underline">Run Explorer</Link> after running `POST /analyze`.</p>}
    </main>
  );
}
