#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Starting MFlux Studio... (project: $PROJECT_DIR)"

# Start backend
cd "$PROJECT_DIR/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
uv pip install -r requirements.txt -q
HOST="${HOST:-127.0.0.1}"
echo "Backend starting on http://${HOST}:8765"
echo "  (set HOST=0.0.0.0 env var for LAN access)"
uvicorn app.main:app --host $HOST --port 8765 --reload &
BACKEND_PID=$!

# Start frontend
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    npm install
fi
echo "Frontend starting on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "MFlux Studio is running!"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8765"
echo "  API Docs: http://localhost:8765/docs"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
