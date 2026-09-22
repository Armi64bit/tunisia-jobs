# TunisJobs frontend

Dark-mode Next.js + TypeScript frontend for the Tunisia jobs scraper. Mirrors the
self-contained prototype in the repository root `index.html`.

## Features

- **Overview** — stats, jobs-by-source bars, top employers, filterable job list.
- **Scraper run** — CV (PDF) upload with drag & drop, live per-source pipeline
  progress, and a run log.
- **CV matches** — jobs ranked against your CV's skill coverage with score bars
  and covered/missing skill chips. Click any match to expand offer and company
  details, a plain-language match rationale, and an apply action. On mobile,
  expanded actions stack at full width, long details wrap safely, and generated
  letters stay within a scrollable preview.

## Run it

```bash
npm install
npm run dev
```

Open http://localhost:3000.

> Data shown is sample data, clearly labeled in the UI. To use your real
> scraper output, point the app at an API and implement the fetch callbacks in
> `lib/api.ts`.

## Configuration

| Variable                  | Purpose                                              |
| ------------------------- | ---------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | Base URL of the scraper backend; unset → demo data. |

## Scripts

```bash
npm run dev        # dev server
npm run build      # production build
npm run lint       # eslint
npm run typecheck  # tsc --noEmit
```