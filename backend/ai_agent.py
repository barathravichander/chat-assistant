import os
from typing import Optional
import google.generativeai as genai

class AIAgent:
    """
    AI Moderator for renewable energy chat using Google Gemini.
    Stays quiet but responds when relevant topics or questions are detected.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.name = "Jarvis"
        
        # Keywords that trigger AI responses
        self.triggers = [
            'help', 'question', 'how', 'what', 'why', 'when', 'where',
            'solar', 'wind', 'hydro', 'renewable', 'energy', 'power',
            'efficiency', 'cost', 'installation', 'maintenance', 'battery',
            'grid', 'panel', 'turbine', 'carbon', 'emission', 'geothermal',
            'biomass', 'tidal', 'wave', 'nuclear', 'fusion'
        ]
        
        # Initialize Google Gemini
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        
        self.system_prompt = """You are Jarvis, a knowledgeable and helpful renewable energy expert moderator.

Guidelines:
- Stay concise and helpful - keep responses under 3-4 sentences unless asked for details.
- Focus on: solar, wind, hydro, geothermal, biomass, energy storage, grid integration, and sustainability.
- Provide accurate, up-to-date information about renewable energy technologies.
- Be encouraging and supportive of clean energy adoption.
- Keep a friendly, conversational tone like a helpful moderator.
- Avoid being preachy - just provide facts and answer questions."""
    
    def should_respond(self, message: str) -> bool:
        """
        Determine if the AI should respond to a message.
        Responds to questions or messages containing trigger keywords.
        """
        message_lower = message.lower()
        
        # Check if it's a question
        if '?' in message:
            return True
        
        # Check for trigger keywords
        for trigger in self.triggers:
            if trigger in message_lower:
                return True
        
        return False
    
    def format_context_for_n8n(self, conversation_context: list) -> str:
        """
        Format conversation context for N8N workflow.
        
        Args:
            conversation_context: List of recent messages
        
        Returns:
            Formatted string of conversation history
        """
        if not conversation_context:
            return ""
        
        context_str = "\n".join([
            f"{msg.get('author', 'User')}: {msg.get('content', '')}" 
            for msg in conversation_context[-10:]  # Last 10 messages
        ])
        return context_str
    
    def moderate_content(self, message: str) -> tuple[bool, Optional[str]]:
        """
        Check if content is appropriate.
        Returns (is_appropriate, warning_message)
        """
        # Simple content moderation
        inappropriate_words = ['spam', 'abuse', 'hate']
        
        message_lower = message.lower()
        for word in inappropriate_words:
            if word in message_lower:
                return False, "Please keep the discussion respectful and on-topic."
        
        return True, None
