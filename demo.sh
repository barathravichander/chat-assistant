#!/bin/bash

# Quick Demo Script for N8N Chat AI Agent
# This script helps you quickly test the chat application with multiple browsers

echo "🚀 Starting N8N Chat AI Agent Demo..."
echo ""

# Check if backend is running
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Backend is already running on port 8001"
else
    echo "⚠️  Backend is not running. Starting it now..."
    cd "$(dirname "$0")/backend"
    python3 main.py &
    BACKEND_PID=$!
    echo "✅ Backend started (PID: $BACKEND_PID)"
    sleep 3
fi

echo ""
echo "📝 Creating default chat rooms..."

# Create rooms
curl -s -X POST http://localhost:8001/rooms/create \
  -H "Content-Type: application/json" \
  -d '{"name":"Solar Energy","description":"Discuss solar power solutions"}' > /dev/null

curl -s -X POST http://localhost:8001/rooms/create \
  -H "Content-Type: application/json" \
  -d '{"name":"Wind Energy","description":"Discuss wind power and turbines"}' > /dev/null

curl -s -X POST http://localhost:8001/rooms/create \
  -H "Content-Type: application/json" \
  -d '{"name":"General Discussion","description":"General renewable energy topics"}' > /dev/null

echo "✅ Rooms created: Solar Energy, Wind Energy, General Discussion"
echo ""

# Get the frontend path
FRONTEND_PATH="$(dirname "$0")/frontend/index.html"

echo "🌐 Opening 3 browser windows..."
echo ""

# Open browsers
if command -v open &> /dev/null; then
    # macOS
    open -a "Google Chrome" "$FRONTEND_PATH" 2>/dev/null || open "$FRONTEND_PATH"
    sleep 1
    open -a "Firefox" "$FRONTEND_PATH" 2>/dev/null || open "$FRONTEND_PATH"
    sleep 1
    open -a "Safari" "$FRONTEND_PATH" 2>/dev/null || open "$FRONTEND_PATH"
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open "$FRONTEND_PATH" &
    sleep 1
    xdg-open "$FRONTEND_PATH" &
    sleep 1
    xdg-open "$FRONTEND_PATH" &
fi

echo "✅ Browsers opened!"
echo ""
echo "📋 Next Steps:"
echo "   1. In each browser, login with different usernames (Alice, Bob, Charlie)"
echo "   2. Join the 'Solar Energy' room in all browsers"
echo "   3. Start chatting and observe real-time synchronization"
echo ""
echo "💡 Test AI Agent (requires N8N setup):"
echo "   - Ask questions: 'What is solar energy?'"
echo "   - Use keywords: 'I'm interested in solar panels'"
echo "   - General chat: 'Hello everyone!' (AI won't respond)"
echo ""
echo "🔧 To enable AI responses:"
echo "   1. Import n8n-chat-ai-agent.json into N8N"
echo "   2. Configure Google Gemini credentials"
echo "   3. Activate the workflow"
echo "   4. Update .env with your Google API key"
echo ""
echo "📖 See N8N_SETUP.md for detailed instructions"
echo ""
echo "Press Ctrl+C to stop the backend server"
echo ""

# Wait for user to stop
wait
