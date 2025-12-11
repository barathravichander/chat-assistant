#!/bin/bash

# Configuration
BACKEND_PORT=8001
FRONTEND_PORT=3000
N8N_PORT=5678
N8N_DOCKER_IMAGE="n8nio/n8n:latest"

echo "============================================"
echo "    Starting Chat Assistant End-to-End"
echo "============================================"
echo ""

# 1. Check Prerequisites
echo "[1/4] Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 could not be found."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker could not be found."
    exit 1
fi

# Check for .env
if [ ! -f .env ]; then
    echo "⚠️  .env file not found! Copying .env.example..."
    cp .env.example .env
    echo "⚠️  Please check .env and add your GOOGLE_API_KEY"
fi

echo "✅ Prerequisites OK"
echo ""

# 2. Start Backend
echo "[2/4] Starting Backend..."

# Kill existing backend if running
if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo "   Killing existing process on port $BACKEND_PORT..."
    lsof -ti :$BACKEND_PORT | xargs kill -9
fi

cd backend
# Use nohup to keep it running
nohup python3 main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo "✅ Backend started (PID: $BACKEND_PID). Log: backend.log"
echo ""

# 3. Start Frontend
echo "[3/4] Starting Frontend..."
# Kill existing frontend if running
if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
    echo "   Killing existing process on port $FRONTEND_PORT..."
    lsof -ti :$FRONTEND_PORT | xargs kill -9
fi

cd frontend
nohup python3 -m http.server $FRONTEND_PORT > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "✅ Frontend started (PID: $FRONTEND_PID). Log: frontend.log"
echo ""

# 4. Start N8N
echo "[4/4] Starting N8N..."

# Check if port 5678 is already in use
if lsof -i :$N8N_PORT > /dev/null 2>&1; then
    echo "   ✅ Port $N8N_PORT is already in use. Assuming N8N is running."
    # Optional: Check which container
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' --filter "publish=$N8N_PORT")
    if [ ! -z "$CONTAINER_NAME" ]; then
        echo "   Running in container: $CONTAINER_NAME"
    fi
else
    # Check if n8n container exists but is stopped
    if docker ps -a --format '{{.Names}}' | grep -q "^n8n$"; then
        echo "   Starting existing n8n container..."
        docker start n8n
    else
        echo "   Starting new n8n container..."
        docker run -d \
            --name n8n \
            -p $N8N_PORT:$N8N_PORT \
            -e N8N_PORT=$N8N_PORT \
            -e WEBHOOK_URL=http://localhost:$N8N_PORT/ \
            $N8N_DOCKER_IMAGE
    fi
    echo "✅ N8N started."
fi
echo ""

echo "Waiting for services to initialize..."
sleep 5

# Final Status Check
./check_status.sh

echo ""
echo "============================================"
echo "          All Services Started"
echo "============================================"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend:  http://localhost:$BACKEND_PORT"
echo "N8N:      http://localhost:$N8N_PORT"
echo ""
echo "To stop everything, you can run: kill $BACKEND_PID $FRONTEND_PID && docker stop n8n"
