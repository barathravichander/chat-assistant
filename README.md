# Renewable Energy Chat Application

Multi-room chat application with AI moderator for renewable energy discussions.

## Architecture

- **Frontend**: Vanilla JavaScript (HTML/CSS/JS)
- **Backend**: Python FastAPI with WebSocket support
- **AI Agent**: Phi/Agno framework with Google Gemini 2.0 Flash + DuckDuckGo search

## Project Structure

```
├── frontend/          # Web UI
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── backend/           # Python API
│   ├── main.py       # FastAPI server
│   ├── ai_agent.py   # Phi Agent moderator
│   └── models.py     # Data models
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure API Key:**
```bash
cp .env.example .env
# Edit .env and add your Google Gemini API key
```

**To get your Google Gemini API key:**
- Visit: https://makersuite.google.com/app/apikey
- Create a new API key (free tier available)
- Copy the key and paste it in `.env` file:
  ```
  GOOGLE_API_KEY=your_actual_api_key_here
  ```

3. **Run the backend:**
```bash
cd backend
python main.py
```

4. **Open frontend:**
```bash
open frontend/index.html
```

## Features

- Multi-room chat (Solar, Wind, Hydro, General)
- Real-time WebSocket communication
- **AI moderator using N8N workflow:**
  - Google Gemini 2.0 Flash for fast, intelligent responses
  - Probabilistic response logic (doesn't respond to every message)
  - Context-aware conversations
  - Stays quiet, responds only when relevant (30% for keywords, 80% for questions)
- User authentication and room management
- Multi-browser support with real-time synchronization

## Quick Demo

Run the demo script to quickly test with 3 browsers:

```bash
./demo.sh
```

This will:
- Start the backend server on port 8001
- Create default chat rooms
- Open 3 browser windows
- Guide you through testing

## AI Agent

The AI moderator (Jarvis) uses **N8N workflow** instead of embedded AI:
- **Agentic approach**: AI runs independently in N8N
- **Probabilistic responses**: 30% for keywords, 80% for questions
- **Context awareness**: Fetches last 10 messages for context
- **Smart triggering**: Avoids consecutive AI messages
- **Observable**: See AI decision-making in N8N execution logs

### N8N Workflow Architecture

```
User Message → Backend API → N8N Webhook
                                 ↓
                         Get Conversation Context
                                 ↓
                         Decision: Should Respond?
                                 ↓
                         Google Gemini AI
                                 ↓
                         Post AI Message → All Users
```

See [`N8N_SETUP.md`](N8N_SETUP.md) for detailed setup instructions.

## API Endpoints

### Create Room
```bash
POST http://localhost:8000/rooms/create
Content-Type: application/json

{
  "name": "Solar Energy",
  "description": "Discuss solar power solutions"
}
```
**Response:**
```json
{
  "status": "created",
  "room": {
    "id": 1,
    "name": "Solar Energy",
    "description": "Discuss solar power solutions",
    "users": []
  }
}
```

### Get All Rooms
```bash
GET http://localhost:8000/rooms
```
**Response:**
```json
[
  {
    "id": 1,
    "name": "Solar Energy",
    "description": "Discuss solar power solutions",
    "users": ["user1", "user2"]
  }
]
```

### Delete Room
```bash
DELETE http://localhost:8000/rooms/{room_id}
```
**Response:**
```json
{
  "status": "deleted",
  "room_id": 1
}
```

### Get Room Messages
```bash
GET http://localhost:8000/rooms/{room_id}/messages
```
**Response:**
```json
[
  {
    "id": "uuid-here",
    "room_id": 1,
    "author": "user1",
    "content": "What's the best solar panel?",
    "timestamp": "2024-12-02T10:30:00",
    "message_type": "user"
  }
]
```

### Join Room
```bash
POST http://localhost:8000/rooms/join
Content-Type: application/json

{
  "username": "john_doe",
  "room_id": 1
}
```
**Response:**
```json
{
  "status": "joined",
  "room": {
    "id": 1,
    "name": "Solar Energy",
    "description": "Discuss solar power solutions",
    "users": ["john_doe"]
  }
}
```

### Leave Room
```bash
POST http://localhost:8000/rooms/leave
Content-Type: application/json

{
  "username": "john_doe",
  "room_id": 1
}
```
**Response:**
```json
{
  "status": "left"
}
```

### Send Message
```bash
POST http://localhost:8000/messages/send
Content-Type: application/json

{
  "username": "john_doe",
  "room_id": 1,
  "content": "How efficient are modern solar panels?"
}
```
**Response:**
```json
{
  "status": "sent",
  "message": {
    "id": "uuid-here",
    "room_id": 1,
    "author": "john_doe",
    "content": "How efficient are modern solar panels?",
    "timestamp": "2024-12-02T10:30:00",
    "message_type": "user"
  }
}
```

### WebSocket Connection
```bash
ws://localhost:8000/ws/{username}
```
**Receives real-time messages:**
```json
{
  "type": "message",
  "room_id": 1,
  "message": {
    "id": "uuid-here",
    "room_id": 1,
    "author": "Jarvis",
    "content": "Modern solar panels typically achieve 15-22% efficiency...",
    "timestamp": "2024-12-02T10:30:05",
    "message_type": "ai"
  }
}
```

## Testing with cURL

```bash
# Create a room
curl -X POST http://localhost:8000/rooms/create \
  -H "Content-Type: application/json" \
  -d '{"name":"Solar Energy","description":"Discuss solar power solutions"}'

# Get all rooms
curl http://localhost:8000/rooms

# Join a room
curl -X POST http://localhost:8000/rooms/join \
  -H "Content-Type: application/json" \
  -d '{"username":"test_user","room_id":1}'

# Send a message
curl -X POST http://localhost:8000/messages/send \
  -H "Content-Type: application/json" \
  -d '{"username":"test_user","room_id":1,"content":"What is solar energy?"}'

# Get room messages
curl http://localhost:8000/rooms/1/messages

# Delete a room
curl -X DELETE http://localhost:8000/rooms/1
```
