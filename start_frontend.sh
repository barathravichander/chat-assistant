#!/bin/bash

echo "Starting Frontend Server..."
echo ""

cd frontend

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    echo "[OK] Starting HTTP server on http://localhost:3000"
    echo ""
    echo "Open in your browser:"
    echo "   http://localhost:3000"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    python3 -m http.server 3000
else
    echo "[ERROR] Python 3 not found"
    exit 1
fi
