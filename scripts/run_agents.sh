#!/usr/bin/env bash
# Start the three Fetch.ai uAgents as independent processes.
# Use this to demonstrate genuine inter-process uAgents messaging.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
  echo "Run scripts/run_dev.sh first to create the virtual environment." >&2
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Starting Research Agent on :8001 ..."
python -m agents.research_agent &
RESEARCH_PID=$!

echo "Starting Language Agent on :8002 ..."
python -m agents.language_agent &
LANGUAGE_PID=$!

echo "Starting Guidance Agent on :8003 ..."
python -m agents.guidance_agent &
GUIDANCE_PID=$!

trap 'echo "Stopping agents..."; kill $RESEARCH_PID $LANGUAGE_PID $GUIDANCE_PID 2>/dev/null || true' EXIT INT TERM

echo ""
echo "Three uAgents running. Fetch.ai addresses are printed above."
echo "Press Ctrl+C to stop."
wait
