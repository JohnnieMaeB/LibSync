# LibSync frontend (`app/`)

Vite + React + TypeScript. This is the source of truth for the LibSync UI, per
[TIER4_PLAN.md](../TIER4_PLAN.md). GitHub Pages is published from the `gh-pages` branch by
[`scripts/build-site.js`](../scripts/build-site.js) + the deploy workflows — see
[README § PR Previews and Deployment](../README.md#-pr-previews-and-deployment).

## Commands

```bash
npm install
npm run dev      # local dev server
npm test         # Vitest + React Testing Library
npm run build    # builds into app/dist (gitignored) — what the deploy workflows publish
```

By default the app talks to the deployed backend (`https://libsync.onrender.com`).
To point at a local `server/` instance instead, create `.env.local`:

```
VITE_API_BASE_URL=http://localhost:3000
```

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the full system design.
