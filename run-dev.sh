#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
  echo "Created backend/.env from example. Add ANAKIN_API_KEY before running live searches."
fi

if [ ! -f "$ROOT_DIR/frontend/.env.local" ]; then
  cp "$ROOT_DIR/frontend/.env.local.example" "$ROOT_DIR/frontend/.env.local"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is not installed. Install Node.js LTS."
  exit 1
fi

echo "Installing backend dependencies..."
uv sync --project "$ROOT_DIR/backend"

echo "Installing frontend dependencies..."
npm --prefix "$ROOT_DIR/frontend" install

echo "Starting backend on :8000 and frontend on :3000"
trap 'kill 0' EXIT

PYTHONPATH="$ROOT_DIR/backend" uv run --project "$ROOT_DIR/backend" uvicorn app.main:app --reload --port 8000 &
npm --prefix "$ROOT_DIR/frontend" run dev
