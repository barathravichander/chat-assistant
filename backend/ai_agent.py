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
        Use AI to intelligently determine if the message warrants a response.
        Considers: intent, topic relevance, conversation context, and user needs.
        """
        # Skip very short messages
        if len(message.strip()) < 3:
            return False
        
        # Use AI to classify the message intent
        try:
            classification_prompt = f"""Analyze this message and determine if an AI renewable energy assistant should respond.

Message: "{message}"

Respond with ONLY "YES" or "NO" based on these criteria:
- YES if: asking a question, seeking information, requesting help, discussing energy/sustainability topics, showing confusion, asking for explanation, or engaging in meaningful dialogue
- NO if: simple greetings (hi, hello, bye), acknowledgments (ok, thanks, got it), off-topic casual chat, or messages clearly not seeking AI input

Your response (YES or NO only):"""

            response = self.model.generate_content(
                classification_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0.1
                )
            )
            
            result = response.text.strip().upper()
            should_respond = "YES" in result
            
            # Log the decision for debugging
            print(f"[AI Agent] Message: '{message[:50]}...' → Respond: {should_respond}")
            
            return should_respond
            
        except Exception as e:
            print(f"[AI Agent] Classification error: {e}, falling back to keyword matching")
            # Fallback to simple keyword matching if AI fails
            return self._keyword_based_check(message)
    
    def _keyword_based_check(self, message: str) -> bool:
        """Fallback keyword-based response check."""
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
