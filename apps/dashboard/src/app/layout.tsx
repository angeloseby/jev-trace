import "./globals.css";
import Link from "next/link";

export const metadata = { title: "JevTrace Dashboard", description: "Agent Failure Intelligence" };

function Nav() {
  return (
    <nav className="border-b bg-white">
      <div className="mx-auto max-w-6xl flex items-center gap-6 px-8 py-3 text-sm">
        <Link href="/" className="font-bold">JevTrace</Link>
        <Link href="/runs" className="text-zinc-600 hover:text-zinc-900">Runs</Link>
        <Link href="/analytics" className="text-zinc-600 hover:text-zinc-900">Analytics</Link>
        <Link href="/components" className="text-zinc-600 hover:text-zinc-900">Components</Link>
        <Link href="/graph" className="text-zinc-600 hover:text-zinc-900">Graph</Link>
        <Link href="/settings" className="ml-auto text-zinc-600 hover:text-zinc-900">Settings → Keys</Link>
      </div>
    </nav>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-50 text-zinc-900 antialiased"><Nav />{children}</body>
    </html>
  );
}
