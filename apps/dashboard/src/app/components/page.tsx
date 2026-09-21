"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchComponents, fetchGraph, fetchRuns } from "@/lib/api";

export default function ComponentsPage(){
  const [data,setData]=useState<Record<string,number>|null>(null);
  const [err,setErr]=useState<string|null>(null);
  useEffect(()=>{ fetchComponents().then(setData).catch((e:any)=>setErr(String(e))); },[]);
  return (
    <main className="mx-auto max-w-4xl p-8">
      <Link href="/" className="text-sm text-zinc-500">← Home</Link>
      <h1 className="mt-2 text-2xl font-bold">Component Health</h1>
      <p className="text-sm text-zinc-600">`GET /api/v1/analytics/components` • planner/retriever/… reliability</p>
      {err && <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{err}</div>}
      <div className="mt-6 rounded-xl border bg-white p-6">
        {!data ? <p className="text-sm text-zinc-500">Loading…</p> :
          <ul className="space-y-2">
            {Object.entries(data).sort((a,b)=>b[1]-a[1]).map(([k,v])=>(
              <li key={k} className="flex items-center gap-3">
                <span className="w-28 text-sm">{k}</span>
                <div className="h-3 flex-1 rounded bg-zinc-100"><div className="h-3 rounded bg-zinc-900" style={{width:`${v*100}%`}}/></div>
                <span className="w-14 text-right text-sm">{(v*100).toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        }
      </div>
      <p className="mt-4 text-xs text-zinc-500">Heuristic: healthy = 1 - (failures attributed to component / total steps for component). Improve via Who&When Pro benchmarking.</p>
    </main>
  );
}
