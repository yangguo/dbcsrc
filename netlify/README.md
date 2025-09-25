# Penalty Case Search (Netlify)

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

## Deploy to Netlify
1. Install Netlify CLI: `npm install -g netlify-cli`
2. Login to Netlify: `netlify login`
3. Initialize project: `netlify init`
4. Set environment variables in Netlify dashboard
5. Deploy: `netlify deploy --prod`

Note: For Netlify deployment, the API routes will automatically work as serverless functions.