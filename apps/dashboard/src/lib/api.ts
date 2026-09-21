export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { cache: "no-store", ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) throw new Error(`${url} ${r.status} ${await r.text().then(t=>t.slice(0,500))}`);
  return r.json() as Promise<T>;
}

export type Run = { id: string; task_name: string; status: string; started_at: string; ended_at?: string; total_steps: number };
export type CursorPage<T> = { items: T[]; next_cursor: string | null; has_more: boolean };
export type Step = { id: string; run_id: string; step_number: number; component: string; status: string; input: any; output: any; latency_ms: number | null; created_at: string };
export type Attribution = { run_id: string; responsible_component: string; component_confidence: number; failure_step: number | null; failure_category: string; category_confidence: number; severity: number };
export type Graph = { nodes: { id: string; weight: number }[]; edges: { source: string; target: string }[] };
export type Recommendation = { recommendation: string; confidence: number };

export type Project = { id: string; name: string; created_at: string };
export type ApiKey = { id: string; project_id: string; public_key: string; name: string | null; created_at: string };
export type ApiKeyWithSecret = ApiKey & { secret_key: string };

export async function fetchProjects() { return j<Project[]>(`${API_BASE}/api/v1/projects`); }
export async function createProject(name: string) { return j<Project>(`${API_BASE}/api/v1/projects`, { method: "POST", body: JSON.stringify({ name }) }); }
export async function fetchApiKeys(projectId: string) { return j<ApiKey[]>(`${API_BASE}/api/v1/projects/${projectId}/api-keys`); }
export async function createApiKey(projectId: string, name?: string) { return j<ApiKeyWithSecret>(`${API_BASE}/api/v1/projects/${projectId}/api-keys`, { method: "POST", body: JSON.stringify({ name }) }); }
export async function ingestBatch(batch: any[], publicKey?: string, secretKey?: string) {
  const headers: Record<string,string> = {};
  if (publicKey && secretKey) { const tok = btoa(`${publicKey}:${secretKey}`); headers["Authorization"] = `Basic ${tok}`; }
  else if (publicKey) headers["X-Api-Key"] = publicKey;
  return j(`${API_BASE}/api/v1/ingest`, { method: "POST", body: JSON.stringify({ batch }), headers });
}

export async function fetchRuns(params?: { status?: string; limit?: number; cursor?: string; project_id?: string; q?: string }) {
  const q = new URLSearchParams(params as any).toString();
  return j<CursorPage<Run>>(`${API_BASE}/api/v1/runs${q ? `?${q}` : ""}`);
}
export async function fetchRun(id: string) { return j<Run>(`${API_BASE}/api/v1/runs/${id}`); }
export async function fetchSteps(runId: string) { return j<CursorPage<Step>>(`${API_BASE}/api/v1/runs/${runId}/steps`); }
export async function fetchAttribution(runId: string) { return j<Attribution>(`${API_BASE}/api/v1/runs/${runId}/attribution`); }
export async function fetchGraph(runId: string) { return j<Graph>(`${API_BASE}/api/v1/runs/${runId}/graph`); }
export async function fetchRecommendations(runId: string) { return j<{ recommendations: Recommendation[] }>(`${API_BASE}/api/v1/runs/${runId}/recommendations`); }
export async function fetchFailures() { return j<Record<string, number>>(`${API_BASE}/api/v1/analytics/failures`); }
export async function fetchComponents() { return j<Record<string, number>>(`${API_BASE}/api/v1/analytics/components`); }
export async function fetchTrends() { return j<{ series: { date: string; failures: number }[] }>(`${API_BASE}/api/v1/analytics/trends`); }

export async function createRun(task_name: string) {
  return j<Run>(`${API_BASE}/api/v1/runs`, { method: "POST", body: JSON.stringify({ task_name }) });
}
export async function completeRun(id: string, status: string) {
  return j(`${API_BASE}/api/v1/runs/${id}/complete`, { method: "POST", body: JSON.stringify({ status }) });
}
export async function analyzeRun(id: string) {
  return j(`${API_BASE}/api/v1/runs/${id}/analyze`, { method: "POST" });
}
export async function login(email: string, password: string) {
  return j(`${API_BASE}/api/v1/auth/login`, { method: "POST", body: JSON.stringify({ email, password }) });
}
