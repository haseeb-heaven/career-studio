#!/bin/bash
# One-click build and run for AI Career Studio (Unix/Git Bash)

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=== 1. Building Frontend ==="
cd "$SCRIPT_DIR/frontend"
npm install
npm run build

echo -e "\n=== 2. Setting up Backend ==="
cd "$SCRIPT_DIR/backend"
# Try using D:/henv/Scripts/pip if it exists (Windows/Git Bash), otherwise standard virtualenv
if [ -f "D:/henv/Scripts/pip" ]; then
    D:/henv/Scripts/pip install -r requirements.txt
    PYTHON_CMD="D:/henv/Scripts/python"
    UVICORN_CMD="D:/henv/Scripts/uvicorn"
elif [ -f "D:/henv/Scripts/pip.exe" ]; then
    D:/henv/Scripts/pip.exe install -r requirements.txt
    PYTHON_CMD="D:/henv/Scripts/python.exe"
    UVICORN_CMD="D:/henv/Scripts/uvicorn.exe"
else
    # Fallback to local .venv or system python
    if [ ! -d ".venv" ]; then
        python -m venv .venv
    fi
    source .venv/bin/activate
    pip install -r requirements.txt
    PYTHON_CMD="python"
    UVICORN_CMD="uvicorn"
fi

echo -e "\n=== 3. Launching Services ==="
# Start backend in background
"$UVICORN_CMD" main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend in background
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo -e "\n[SUCCESS] Services started in the background!"
echo "- Backend PID: $BACKEND_PID (running at http://localhost:8000)"
echo "- Frontend PID: $FRONTEND_PID (running at http://localhost:5173)"
echo "Press Ctrl+C to terminate both services."

# Trap to kill background processes on exit
trap "echo -e '\nStopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" SIGINT SIGTERM EXIT
wait
