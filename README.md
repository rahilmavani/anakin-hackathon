# TenderFlow Hackathon Scaffold

Perplexity-style streaming UI + FastAPI/LangGraph backend for Anakin-powered tender discovery.

## Stack

- Frontend: Next.js + Tailwind (`frontend/`)
- Backend: FastAPI + LangGraph + httpx (`backend/`)

## Run Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

## Current Flow

1. Parse user intent
2. Build tender-focused search queries
3. Call Anakin Search API
4. Deduplicate and batch scrape URLs with Anakin URL Scraper
5. Extract normalized tender objects from `generatedJson`
6. Score and rank tenders
7. Stream tool calls + sources + final result over SSE

## Important Notes

- If `ANAKIN_API_KEY` is missing, backend still runs but returns no live sources.
- This is an MVP architecture scaffold; extraction prompt hardening and schema validation can be deepened next.
