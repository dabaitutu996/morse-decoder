#!/bin/bash
set -e

cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Starting Morse Decoder server at http://localhost:9000"
python server/main.py &
SERVER_PID=$!

sleep 2
open http://localhost:9000

wait $SERVER_PID
