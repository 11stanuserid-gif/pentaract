#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Signup Shield Auditor — Launch Script
# Starts both the FastAPI backend and Vite frontend dev server.
# ─────────────────────────────────────────────────────────────
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# ── Colors ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Signup Shield Auditor — Launcher      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Setup virtual environment ───────────────────────────
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo -e "${CYAN}[setup] Creating Python virtual env...${NC}"
    python3 -m venv "$BACKEND_DIR/.venv"
fi
echo -e "${CYAN}[setup] Installing Python dependencies...${NC}"
"$BACKEND_DIR/.venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"

# ── Check Playwright ────────────────────────────────────
if ! "$BACKEND_DIR/.venv/bin/python" -c "from playwright.sync_api import sync_playwright; sync_playwright().__enter__()" 2>/dev/null; then
    echo -e "${CYAN}[setup] Installing Playwright Chromium...${NC}"
    "$BACKEND_DIR/.venv/bin/python" -m playwright install chromium
fi

# ── Install frontend deps ───────────────────────────────
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${CYAN}[setup] Installing frontend dependencies...${NC}"
    cd "$FRONTEND_DIR" && npm install --silent
fi

# ── Cleanup on exit ─────────────────────────────────────
cleanup() {
    echo ""
    echo -e "${RED}[shutdown] Stopping servers...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    echo -e "${RED}[shutdown] Done.${NC}"
}
trap cleanup EXIT INT TERM

# ── Start backend ───────────────────────────────────────
echo -e "${GREEN}[backend] Starting API server on http://127.0.0.1:8000${NC}"
cd "$BACKEND_DIR"
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 2

# ── Start frontend ──────────────────────────────────────
echo -e "${GREEN}[frontend] Starting dev server on http://127.0.0.1:5173${NC}"
cd "$FRONTEND_DIR"
npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Frontend:  http://127.0.0.1:5173            ║${NC}"
echo -e "${CYAN}║  Backend:   http://127.0.0.1:8000            ║${NC}"
echo -e "${CYAN}║  Press Ctrl+C to stop both servers.          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
