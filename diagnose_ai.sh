#!/bin/bash

echo "🔍 AI Agent Diagnostics"
echo "======================="
echo ""

# 1. Check if backend is running
echo "1️⃣ Backend Status:"
if lsof -i :8001 > /dev/null 2>&1; then
    echo "   ✅ Backend running on port 8001"
else
    echo "   ❌ Backend NOT running"
    exit 1
fi

# 2. Check if N8N is running
echo ""
echo "2️⃣ N8N Status:"
if lsof -i :5678 > /dev/null 2>&1; then
    echo "   ✅ N8N running on port 5678"
else
    echo "   ❌ N8N NOT running"
    exit 1
fi

# 3. Check .env configuration
echo ""
echo "3️⃣ Environment Configuration:"
if [ -f ".env" ]; then
    if grep -q "N8N_WEBHOOK_URL" .env; then
        WEBHOOK_URL=$(grep "N8N_WEBHOOK_URL" .env | cut -d'=' -f2)
        echo "   ✅ N8N_WEBHOOK_URL configured: $WEBHOOK_URL"
    else
        echo "   ❌ N8N_WEBHOOK_URL not found in .env"
    fi
    
    if grep -q "GOOGLE_API_KEY" .env; then
        echo "   ✅ GOOGLE_API_KEY configured"
    else
        echo "   ❌ GOOGLE_API_KEY not found in .env"
    fi
else
    echo "   ❌ .env file not found"
fi

# 4. Check if rooms exist
echo ""
echo "4️⃣ Rooms Status:"
ROOMS=$(curl -s http://localhost:8001/rooms)
if [ "$ROOMS" = "[]" ]; then
    echo "   ⚠️  No rooms created yet"
    echo "   💡 Create a room in the chat app first"
else
    echo "   ✅ Rooms exist: $ROOMS"
fi

# 5. Test N8N webhook
echo ""
echo "5️⃣ Testing N8N Webhook:"
echo "   Sending test message to N8N..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:5678/webhook/chat-ai-agent \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "message": "What is solar energy?",
    "author": "diagnostic",
    "timestamp": "2024-12-02T15:50:00"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "   ✅ N8N webhook responding (HTTP $HTTP_CODE)"
else
    echo "   ⚠️  N8N webhook returned HTTP $HTTP_CODE"
fi

# 6. Check N8N workflow status
echo ""
echo "6️⃣ N8N Workflow Check:"
echo "   Open http://localhost:5678/executions to see workflow runs"
echo "   Look for 'Chat AI Agent (EcoBot)' executions"

# 7. Common issues
echo ""
echo "🔧 Common Issues:"
echo ""
echo "   ❌ AI not responding?"
echo "      → Check N8N workflow is ACTIVE (green toggle)"
echo "      → Verify Google Gemini credentials in N8N"
echo "      → Check N8N executions for errors"
echo "      → Ensure room exists before sending messages"
echo ""
echo "   ❌ 'Get Conversation Context' fails?"
echo "      → Room doesn't exist (create room first)"
echo "      → Backend not running on port 8001"
echo "      → Check N8N node URL: http://localhost:8001/api/context/{{$json.room_id}}"
echo ""
echo "   ❌ Google Gemini fails?"
echo "      → API key not configured in N8N credentials"
echo "      → Invalid API key"
echo "      → Rate limit exceeded"
echo ""

echo "📊 Next Steps:"
echo "   1. Open N8N: http://localhost:5678"
echo "   2. Go to Executions tab"
echo "   3. Check latest execution for errors"
echo "   4. If no executions, workflow might not be active"
echo ""
