#!/usr/bin/env bash
# Start the AccessBridge AI dev stack: backend + frontend.
# Agents run in embedded mode by default (no separate processes needed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- Backend ---
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing backend deps..."
pip install -q -r requirements.txt

echo "Initialising database..."
python -c "from backend.app.database import init_db; init_db()"

echo "Starting backend on :8000 ..."
uvicorn backend.app.main:app --reload --port 8000 &
BACKEND_PID=$!

# --- Frontend ---
(
  cd frontend
  if [ ! -d "node_modules" ]; then
    echo "Installing frontend deps..."
    npm install
  fi
  echo "Starting frontend on :5173 ..."
  npm run dev
) &
FRONTEND_PID=$!

trap 'echo "Stopping..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT INT TERM

echo ""
echo "AccessBridge AI is running:"
echo "  Backend:  http://localhost:8000  (docs: /docs)"
echo "  Frontend: http://localhost:5173"
echo "  Health:   http://localhost:8000/api/health"
echo ""
echo "Press Ctrl+C to stop."
wait
