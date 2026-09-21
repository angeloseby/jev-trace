import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-3xl font-bold">JevTrace — Agent Failure Intelligence</h1>
      <p className="mt-2 text-zinc-600">Runs → Trace Explorer → Attribution → Graph → Analytics</p>
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { href: "/runs", label: "Run Explorer" },
          { href: "/analytics", label: "Failure Analytics" },
          { href: "/components", label: "Component Health" },
          { href: "/graph", label: "Attribution Graph" },
        ].map((c) => (
          <Link key={c.href} href={c.href} className="rounded-xl border bg-white p-6 hover:shadow">
            {c.label}
          </Link>
        ))}
      </div>
      <div className="mt-8 rounded-xl border bg-white p-6">
        <h2 className="font-semibold">API</h2>
        <p className="text-sm text-zinc-600">Backend at <code>http://localhost:8000/api/v1</code> — see <code>/docs</code> for OpenAPI.</p>
      </div>
    </main>
  );
}
