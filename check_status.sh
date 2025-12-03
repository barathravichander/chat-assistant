#!/bin/bash

echo "🔍 Checking System Status..."
echo ""

# Check N8N
echo "1️⃣ N8N Status:"
if lsof -i :5678 > /dev/null 2>&1; then
    echo "   ✅ N8N is running on port 5678"
else
    echo "   ❌ N8N is NOT running"
    exit 1
fi

# Check Backend
echo ""
echo "2️⃣ Backend Status:"
if lsof -i :8001 > /dev/null 2>&1; then
    echo "   ✅ Backend is running on port 8001"
else
    echo "   ❌ Backend is NOT running"
    exit 1
fi

# Test N8N Webhook
echo ""
echo "3️⃣ Testing N8N Webhook:"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:5678/webhook/chat-ai-agent \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "message": "What is solar energy?",
    "author": "test",
    "timestamp": "2024-12-02T14:00:00"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "   ✅ N8N webhook responded (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
else
    echo "   ⚠️  N8N webhook returned HTTP $HTTP_CODE"
    echo "   This might mean the workflow isn't imported/activated yet"
    echo "   Response: $BODY"
fi

# Test Backend API
echo ""
echo "4️⃣ Testing Backend API:"
ROOMS=$(curl -s http://localhost:8001/rooms)
echo "   ✅ Backend API responding"
echo "   Rooms: $ROOMS"

echo ""
echo "📋 Summary:"
echo "   • N8N: http://localhost:5678"
echo "   • Backend: http://localhost:8001"
echo "   • Chat App: file://$(pwd)/frontend/index.html"
echo ""
echo "🎯 Next Steps:"
echo "   1. Import workflow in N8N: n8n-chat-ai-agent.json"
echo "   2. Configure Google Gemini credentials in N8N"
echo "   3. Activate the workflow (toggle Active switch)"
echo "   4. Test in chat app!"
