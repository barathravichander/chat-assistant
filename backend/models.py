from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"

class User(BaseModel):
    username: str
    room_id: Optional[int] = None

class Room(BaseModel):
    id: int
    name: str
    description: str
    users: List[str] = []

class Message(BaseModel):
    id: str
    room_id: int
    author: str
    content: str
    timestamp: datetime
    message_type: MessageType = MessageType.USER

class JoinRoomRequest(BaseModel):
    username: str
    room_id: int

class SendMessageRequest(BaseModel):
    username: str
    room_id: int
    content: str

class CreateRoomRequest(BaseModel):
    name: str
    description: str

class AIMessageRequest(BaseModel):
    room_id: int
    content: str
    author: str = "Jarvis"

class ContextMessage(BaseModel):
    author: str
    content: str
    timestamp: datetime
    message_type: MessageType

class ContextResponse(BaseModel):
    room_id: int
    room_name: str
    messages: List[ContextMessage]
    total_messages: int
