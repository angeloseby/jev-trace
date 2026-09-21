# JevTrace Dashboard

Next.js + Tailwind + Recharts.

```bash
npm install
npm run dev    # http://localhost:3000
npm run build
```

Proxies `/api/*` → `http://localhost:8000` via `next.config.js`.
Never call Jev directly — go through `POST /internal/jev/analyze` on the API.
