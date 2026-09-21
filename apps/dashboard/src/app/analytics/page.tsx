"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchFailures, fetchComponents, fetchTrends } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from "recharts";

const COLORS = ["#18181b","#3f3f46","#71717a","#a1a1aa","#d4d4d8"];

export default function AnalyticsPage() {
  const [failures, setFailures] = useState<Record<string,number>|null>(null);
  const [components, setComponents] = useState<Record<string,number>|null>(null);
  const [trends, setTrends] = useState<{date:string; failures:number}[]|null>(null);
  const [err, setErr] = useState<string|null>(null);
  useEffect(()=>{
    Promise.all([fetchFailures().catch(()=>({})), fetchComponents().catch(()=>({})), fetchTrends().catch(()=>({series:[]}))])
      .then(([f,c,t]:any)=>{ setFailures(f); setComponents(c); setTrends(t.series||[]); })
      .catch((e:any)=>setErr(String(e)));
  },[]);

  const failureData = failures ? Object.entries(failures).map(([name,value])=>({name,value})) : [];
  const componentData = components ? Object.entries(components).map(([name,value])=>({name,value})) : [];

  return (
    <main className="mx-auto max-w-6xl p-8">
      <Link href="/" className="text-sm text-zinc-500">← Home</Link>
      <h1 className="mt-2 text-2xl font-bold">Failure Analytics</h1>
      <p className="text-sm text-zinc-600">{'GET /api/v1/analytics/{failures,components,trends}'} • Recharts</p>
      {err && <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{err}</div>}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-4">
          <h2 className="font-semibold">Failure Distribution</h2>
          <p className="text-xs text-zinc-500">GROUP BY failure_category</p>
          <div className="h-64 mt-2">
            {failureData.length? <ResponsiveContainer width="100%" height="100%"><BarChart data={failureData}><XAxis dataKey="name" tick={{fontSize:10}} interval={0} angle={-20} height={60}/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="value" fill="#18181b"/></BarChart></ResponsiveContainer> : <p className="py-12 text-center text-sm text-zinc-500">No data — run some failures then `POST /analyze`</p>}
          </div>
          <div className="mt-2 h-40">
            {failureData.length? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={failureData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} label>{failureData.map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer> : null}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-4">
          <h2 className="font-semibold">Component Reliability</h2>
          <p className="text-xs text-zinc-500">1 - attributed_failures / total_steps</p>
          <div className="h-64 mt-2">
            {componentData.length? <ResponsiveContainer width="100%" height="100%"><BarChart data={componentData}><XAxis dataKey="name" tick={{fontSize:10}} /><YAxis domain={[0,1]}/><Tooltip/><Bar dataKey="value" fill="#3f3f46"/></BarChart></ResponsiveContainer> : <p className="py-12 text-center text-sm text-zinc-500">No data</p>}
          </div>
          <ul className="mt-2 text-xs text-zinc-600">{componentData.map(d=><li key={d.name}>{d.name}: {(d.value*100).toFixed(1)}%</li>)}</ul>
        </section>
      </div>

      <section className="mt-6 rounded-xl border bg-white p-4">
        <h2 className="font-semibold">Failure Trends</h2>
        <p className="text-xs text-zinc-500">`GET /analytics/trends?days=30` • date vs failures</p>
        <div className="h-64 mt-2">
          {trends?.length? <ResponsiveContainer width="100%" height="100%"><LineChart data={trends}><XAxis dataKey="date" tick={{fontSize:10}}/><YAxis allowDecimals={false}/><Tooltip/><Line type="monotone" dataKey="failures" stroke="#18181b" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer> : <p className="py-12 text-center text-sm text-zinc-500">No failed runs yet</p>}
        </div>
      </section>
    </main>
  );
}
