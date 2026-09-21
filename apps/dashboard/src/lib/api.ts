export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchRuns() {
  const r = await fetch(`${API_BASE}/api/v1/runs`, { cache: "no-store" });
  if (!r.ok) throw new Error(`fetchRuns ${r.status}`);
  return r.json();
}
