# N8N AI Agent Setup Guide

This guide explains how to set up the N8N workflow for the **Jarvis** AI moderator.

## Prerequisites

- **N8N** installed and running (default: http://localhost:5678)
- **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/app/apikey))
- **Backend Server** running (default: http://localhost:8001)

## Quick Setup

### Step 1: Import the Workflow

1. Open N8N in your browser: **http://localhost:5678**
2. Click **"Add workflow"** → **"Import from File"**
3. Select the file: `n8n-chat-ai-agent.json` (in the project root)
4. Click **"Import"**

### Step 2: Configure Google API Key

1. In the workflow, click on the **"Call Google Gemini API"** node (it might have a ⚠️ warning)
2. Click **"Credential to connect with"** dropdown
3. Click **"Create New Credential"**
4. Select **"Query Auth"** as the credential type
5. Configure the credential:
   - **Name**: `Google Gemini API Key`
   - **Name**: `key` (must be lowercase "key")
   - **Value**: Paste your Google API Key
6. Click **"Save"**

### Step 3: Activate the Workflow

1. Toggle the **"Active"** switch to **ON** (top right corner)
2. The workflow should now show as ▶️ **Active**

## Verification

You can test the workflow using `curl`:

```bash
curl -X POST http://localhost:5678/webhook/chat-ai-agent \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "message": "What is solar energy?",
    "author": "test",
    "timestamp": "2024-12-02T12:00:00"
  }'
```

**Expected Response:**
```json
{"status": "processed", "responded": true}
```

## Workflow Architecture

The workflow follows this logic:

```
Webhook Trigger
    ↓
Get Conversation Context (from backend API)
    ↓
Decision: Should Respond? (probabilistic logic)
    ↓
IF Should Respond
    ├─ Yes → Build AI Prompt
    │         ↓
    │       Prepare Gemini Request (build JSON body)
    │         ↓
    │       Call Google Gemini API (gemini-2.0-flash)
    │         ↓
    │       Extract AI Response
    │         ↓
    │       Post AI Message to Chat (as "Jarvis")
    │         ↓
    │       Respond: AI Sent
    │
    └─ No → Respond: No AI
```

### AI Response Probability

- **Questions** (with `?`): 80% chance of response
- **Energy keywords** (solar, wind, hydro, etc.): 30% chance
- **General chat**: 0% chance

## Troubleshooting

### Connection Refused
If N8N cannot connect to the backend, ensure the workflow uses `host.docker.internal` instead of `localhost` for backend URLs if N8N is running in Docker. The provided workflow is already configured this way.

### 404 Not Found (Gemini API)
Ensure the workflow is using the correct model name: `gemini-2.0-flash`.

### No Response in Chat
Check the N8N **Executions** tab. If the execution is successful but no message appears, check the backend logs. Remember the response is probabilistic!
