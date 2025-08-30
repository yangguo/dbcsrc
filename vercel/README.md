# Penalty Case Search (Vercel)

Minimal Next.js app with a serverless API for searching penalty cases directly from MongoDB.

## Quick Start
- Copy environment file: `cp .env.example .env.local` and set `MONGODB_URI`.
- Dev: `npm install && npm run dev`
- Build/Start: `npm run build && npm start`

## API
- `GET /api/search`
  - Query params: `keyword`, `docNumber`, `org`, `party`, `minAmount`, `legalBasis`, `dateFrom`, `dateTo`, `page`, `pageSize`.
  - Returns: `{ data: [...], total, page, pageSize }`.

## Env Vars
- `MONGODB_URI`: Mongo connection string.
- `MONGODB_DB` (default `pencsrc2`)
- `MONGODB_COLLECTION` (default `csrc2analysis`)

## Deploy
- Push `vercel/` as a Vercel project root or select this subfolder in Vercel.
- Set env vars in Vercel dashboard.

