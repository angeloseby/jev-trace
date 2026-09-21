"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchRuns, type Run, createRun } from "@/lib/api";

export default function RunsPage() {
  const [data, setData] = useState<{ items: Run[]; next_cursor: string | null; has_more: boolean } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [task, setTask] = useState("answer_question");

  async function load(cursor?: string) {
    try {
      const res = await fetchRuns({ limit: 20, cursor });
      setData(res);
    } catch (e: any) {
      setErr(String(e.message || e));
    }
  }
  useEffect(() => { load(); }, []);

  async function handleCreate() {
    try {
      await createRun(task);
      await load();
    } catch (e: any) { setErr(String(e)); }
  }

  return (
    <main className="mx-auto max-w-5xl p-8">
      <Link href="/" className="text-sm text-zinc-500">← Home</Link>
      <h1 className="mt-2 text-2xl font-bold">Run Explorer</h1>
      <p className="text-sm text-zinc-600">Cursor-paginated • `GET /api/v1/runs?limit=20&cursor=...`</p>

      <div className="mt-4 flex gap-2">
        <input value={task} onChange={e=>setTask(e.target.value)} className="rounded border px-3 py-2 text-sm flex-1" placeholder="task_name" />
        <button onClick={handleCreate} className="rounded bg-zinc-900 px-4 py-2 text-sm text-white">Create run</button>
        <button onClick={()=>load()} className="rounded border px-4 py-2 text-sm">Refresh</button>
      </div>

      {err && <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{err}</div>}
      {!data ? <p className="mt-6 text-sm text-zinc-500">Loading… (ensure API at :8000, `docker compose up`)</p> :
        <div className="mt-6 overflow-hidden rounded-xl border bg-white">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50"><tr><th className="px-4 py-2 text-left">Run</th><th className="px-4 py-2">Status</th><th className="px-4 py-2">Steps</th><th className="px-4 py-2">Started</th></tr></thead>
            <tbody>
              {data.items.map(r=>(
                <tr key={r.id} className="border-t hover:bg-zinc-50">
                  <td className="px-4 py-2"><Link href={`/runs/${r.id}`} className="font-mono text-xs underline">{r.id.slice(0,8)}…</Link><div className="text-xs text-zinc-500">{r.task_name}</div></td>
                  <td className="px-4 py-2 text-center"><span className={`rounded px-2 py-1 text-xs ${r.status==="failed"?"bg-red-100 text-red-700":r.status==="completed"?"bg-green-100 text-green-700":"bg-zinc-100"}`}>{r.status}</span></td>
                  <td className="px-4 py-2 text-center">{r.total_steps}</td>
                  <td className="px-4 py-2 text-xs text-zinc-500">{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
              {data.items.length===0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-zinc-500">No runs yet — create one above or `POST /api/v1/runs`</td></tr>}
            </tbody>
          </table>
          {data.has_more && data.next_cursor && <div className="border-t p-3 text-center"><button onClick={()=>load(data.next_cursor!)} className="text-sm underline">Next page →</button></div>}
        </div>
      }
    </main>
  );
}
