# LibSync frontend (`app/`)

Vite + React + TypeScript. This is the source of truth for the LibSync UI, per
[TIER4_PLAN.md](../TIER4_PLAN.md) — `docs/` is generated from this via `npm run build`
and is never hand-edited.

## Commands

```bash
npm install
npm run dev      # local dev server
npm test         # Vitest + React Testing Library
npm run build    # builds into ../docs (what GitHub Pages serves)
```

By default the app talks to the deployed backend (`https://libsync.onrender.com`).
To point at a local `server/` instance instead, create `.env.local`:

```
VITE_API_BASE_URL=http://localhost:3000
```

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the full system design.
