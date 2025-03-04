import os
import logging
from typing import List, Dict, Any, Optional
import re
import datetime
from openai import OpenAI

from app.database.db import (
    get_bet_recommendations,
    get_historical_bets,
    get_recent_context_bets,
    track_recommendation_usage,
    get_user_plan,
    check_timeout,
    record_violation,
    save_chat_message,
    get_chat_history,
    get_db
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class ChatbotCore:
    """Core chatbot functionality for processing user queries and generating responses."""
    
    def __init__(self):
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt from the file."""
        try:
            with open('app/chatbot/system_prompt.txt', 'r') as file:
                return file.read()
        except FileNotFoundError:
            # Fallback system prompt if file not found
            return """You are a helpful betting assistant. You provide information about sports betting opportunities, 
            historical betting data, and general betting advice. You should not encourage irresponsible gambling 
            and should emphasize responsible betting practices."""
    
    def process_query(self, user_id: int, session_id: str, query: str) -> Dict[str, Any]:
        """
        Process a user query and generate a response.
        
        Args:
            user_id: The ID of the user making the query
            session_id: The session ID for the conversation
            query: The user's query text
            
        Returns:
            A dictionary containing the response and metadata
        """
        # Log the incoming query for debugging
        logger.info(f"Processing query from user_id {user_id}, session {session_id}: '{query}'")
        
        # Check for secret command to get timestamp info (with multiple variations)
        cleaned_query = query.strip().lower()
        if cleaned_query in ["!timestamps", "timestamps", "show timestamps", "admin:timestamps", "##timestamps##"]:
            logger.info(f"Timestamp command detected from user_id {user_id}: '{cleaned_query}'")
            
            # Get user email for special command access
            db = get_db()
            cursor = db.execute("SELECT email, plan FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user:
                user_email = user['email']
                user_plan = user['plan']
                logger.info(f"User email: {user_email}, plan: {user_plan}")
                
                if user_email == "test@example.com":
                    logger.info("Authorized user for timestamp command")
                    timestamp_info = self._get_timestamp_info()
                    response = f"ADMIN COMMAND EXECUTED: Timestamp Information\n\n{timestamp_info}"
                    
                    # Save the response
                    save_chat_message(user_id, session_id, response, "assistant")
                    
                    return {
                        "response": response,
                        "session_id": session_id,
                        "is_secret_command": True
                    }
            
            # For other users, don't reveal the command exists
            logger.info("Unauthorized user attempted timestamp command")
            response = "I'm not sure what you're asking. Could you please rephrase your question?"
            save_chat_message(user_id, session_id, response, "assistant")
            
            return {
                "response": response,
                "session_id": session_id
            }
        
        # Check for timeout
        timeout_until = check_timeout(user_id)
        if timeout_until:
            now = datetime.datetime.now()
            if now < timeout_until:
                time_remaining = timeout_until - now
                hours = time_remaining.seconds // 3600
                minutes = (time_remaining.seconds % 3600) // 60
                time_str = f"{hours} hours and {minutes} minutes" if hours > 0 else f"{minutes} minutes"
                
                return {
                    "response": (f"Your account is currently in a timeout period due to previous violations. "
                                 f"You can use the chatbot again in {time_str}."),
                    "session_id": session_id,
                    "timeout": True,
                    "timeout_until": timeout_until.isoformat()
                }
        
        # Check for violations
        if self._check_for_violation(query):
            violation_count = record_violation(user_id)
            
            if violation_count >= 3:
                return {
                    "response": ("Your account has been temporarily suspended due to multiple violations of our chat rules. "
                                 "Please review our terms of service and try again later."),
                    "session_id": session_id,
                    "violation": True,
                    "violation_count": violation_count
                }
            else:
                return {
                    "response": ("I'm sorry, but I cannot respond to that query as it appears to violate our chat rules. "
                                 "Please refrain from asking about prohibited topics such as match-fixing, illegal betting, "
                                 "or using betting for money laundering."),
                    "session_id": session_id,
                    "violation": True,
                    "violation_count": violation_count
                }
        
        # Save the user message
        save_chat_message(user_id, session_id, query, "user")
        
        # Get chat history
        history = get_chat_history(user_id, session_id)
        
        try:
            # Get betting recommendations (only most recent timestamp)
            recommendations = get_bet_recommendations(query)
            
            # Get recent context bets (within 6 hours but not most recent timestamp)
            # These are not shown to the user but help the chatbot provide context
            context_bets = get_recent_context_bets(query)
            
            # Get historical betting data (older than 6 hours)
            historical_bets = get_historical_bets(query)
            
            # Format the betting data for GPT
            recommendation_context = self._format_bets_for_gpt(recommendations, "Current Betting Recommendations")
            
            # Format context bets (not shown to user but used by GPT)
            context_bets_text = self._format_bets_for_gpt(context_bets, "Recent Context Bets (Not For Direct Recommendation)")
            
            # Format historical data
            historical_context = self._format_bets_for_gpt(historical_bets, "Historical Betting Data")
            
            # Combine all betting context
            combined_context = ""
            if recommendation_context:
                combined_context += recommendation_context + "\n\n"
            if context_bets_text:
                combined_context += context_bets_text + "\n\n"
            if historical_context:
                combined_context += historical_context
                
            # If we have no betting context at all, set to None
            if not combined_context.strip():
                combined_context = None
            
            # Generate response using GPT
            response = self._generate_gpt_response(query, combined_context, history)
            
            # Save the assistant's response
            save_chat_message(user_id, session_id, response, "assistant")
            
            return {
                "response": response,
                "session_id": session_id,
                "has_recommendations": bool(recommendations),
                "recommendation_count": len(recommendations) if recommendations else 0
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            
            # Generate a fallback response
            fallback_response = self._generate_fallback_response(query)
            
            # Save the fallback response
            save_chat_message(user_id, session_id, fallback_response, "assistant")
            
            return {
                "response": fallback_response,
                "session_id": session_id,
                "error": str(e)
            }
    
    def _get_timestamp_info(self) -> str:
        """
        Get information about the timestamps in the betting database.
        This is a secret admin function for debugging purposes.
        
        Returns:
            A formatted string with timestamp information
        """
        db = get_db()
        
        # Get the most recent timestamp
        cursor = db.execute(
            "SELECT MAX(timestamp) as latest_timestamp FROM betting_data WHERE ev_percent > 0"
        )
        result = cursor.fetchone()
        latest_timestamp = result['latest_timestamp'] if result else "No data found"
        
        # Get timestamp range
        cursor = db.execute(
            "SELECT MIN(timestamp) as earliest_timestamp, MAX(timestamp) as latest_timestamp, "
            "COUNT(DISTINCT timestamp) as timestamp_count FROM betting_data"
        )
        result = cursor.fetchone()
        earliest_timestamp = result['earliest_timestamp'] if result else "No data found"
        timestamp_count = result['timestamp_count'] if result else 0
        
        # Get count of bets in most recent timestamp
        cursor = db.execute(
            "SELECT COUNT(*) as bet_count FROM betting_data WHERE timestamp = ?",
            (latest_timestamp,)
        )
        result = cursor.fetchone()
        latest_timestamp_bet_count = result['bet_count'] if result else 0
        
        # Get count of bets in recent context (within 6 hours but not most recent)
        cursor = db.execute(
            "SELECT COUNT(*) as bet_count FROM betting_data WHERE timestamp < ? AND timestamp > datetime(?, '-6 hours')",
            (latest_timestamp, latest_timestamp)
        )
        result = cursor.fetchone()
        recent_context_bet_count = result['bet_count'] if result else 0
        
        # Get count of historical bets (older than 6 hours)
        cursor = db.execute(
            "SELECT COUNT(*) as bet_count FROM betting_data WHERE timestamp <= datetime(?, '-6 hours')",
            (latest_timestamp,)
        )
        result = cursor.fetchone()
        historical_bet_count = result['bet_count'] if result else 0
        
        # Get total bet count
        cursor = db.execute("SELECT COUNT(*) as total_count FROM betting_data")
        result = cursor.fetchone()
        total_bet_count = result['total_count'] if result else 0
        
        # Format the information
        info = f"Most Recent Timestamp: {latest_timestamp}\n"
        info += f"Earliest Timestamp: {earliest_timestamp}\n"
        info += f"Number of Distinct Timestamps: {timestamp_count}\n\n"
        info += f"Bets in Most Recent Timestamp: {latest_timestamp_bet_count}\n"
        info += f"Bets in Recent Context (within 6 hours): {recent_context_bet_count}\n"
        info += f"Historical Bets (older than 6 hours): {historical_bet_count}\n"
        info += f"Total Bets in Database: {total_bet_count}\n"
        
        return info
    
    def _check_for_violation(self, query: str) -> bool:
        """
        Check if the query contains prohibited content.
        
        Args:
            query: The user's query
            
        Returns:
            True if the query contains prohibited content, False otherwise
        """
        # List of prohibited terms and patterns
        prohibited_patterns = [
            r'\b(match[ -]?fix(ing|ed)?)\b',
            r'\b(throw(ing)? (a )?match(es)?)\b',
            r'\b(launder(ing)? money)\b',
            r'\b(illegal (bet(s|ting)?|gambling|wager(s|ing)?))\b',
            r'\b(underage (bet(s|ting)?|gambling|wager(s|ing)?))\b',
            r'\b(cheat(ing)? (the )?system)\b',
            r'\b(avoid(ing)? (gambling )?restrictions)\b',
            r'\b(bypass(ing)? (betting )?limits)\b'
        ]
        
        # Check if any prohibited pattern is in the query
        query_lower = query.lower()
        for pattern in prohibited_patterns:
            if re.search(pattern, query_lower):
                return True
                
        return False
    
    def _format_bets_for_gpt(self, bets: List[Dict[str, Any]], section_title: str = "Betting Opportunities") -> str:
        """
        Format betting data for inclusion in the GPT prompt.
        
        Args:
            bets: List of betting data dictionaries
            section_title: Title for this section of betting data
            
        Returns:
            Formatted string of betting data
        """
        if not bets:
            return ""
            
        formatted_text = f"--- {section_title} ---\n"
        
        for i, bet in enumerate(bets, 1):
            formatted_text += f"{i}. Game: {bet.get('game', 'Unknown')}\n"
            formatted_text += f"   Bet: {bet.get('bet_description', 'Unknown')}\n"
            formatted_text += f"   Sportsbook: {bet.get('sportsbook', 'Unknown')}\n"
            formatted_text += f"   Odds: {bet.get('odds', 'Unknown')}\n"
            formatted_text += f"   EV%: {bet.get('ev_percent', 'Unknown')}%\n"
            formatted_text += f"   Win Probability: {bet.get('win_probability', 'Unknown')}%\n"
            formatted_text += f"   Sport/League: {bet.get('sport', 'Unknown')}/{bet.get('league', 'Unknown')}\n"
            formatted_text += f"   Event Time: {bet.get('event_time', 'Unknown')}\n"
            
            # Add timestamp for context/historical bets but not for recommendations
            if section_title != "Current Betting Recommendations":
                formatted_text += f"   Data Timestamp: {bet.get('timestamp', 'Unknown')}\n"
                
            formatted_text += "\n"
            
        return formatted_text
    
    def _generate_fallback_response(self, query: str) -> str:
        """
        Generate a fallback response when an error occurs.
        
        Args:
            query: The user's query
            
        Returns:
            A fallback response
        """
        fallback_responses = [
            "I'm having trouble processing your request right now. Please try again later.",
            "Sorry, I couldn't retrieve the betting information you requested. Please try a different query.",
            "There was an issue with our betting data service. Please try again in a few moments.",
            "I apologize, but I'm unable to provide betting recommendations at this time. Please try again later."
        ]
        
        # Use a simple hash of the query to select a consistent fallback response
        hash_value = sum(ord(c) for c in query) % len(fallback_responses)
        return fallback_responses[hash_value]
    
    def _generate_gpt_response(self, query: str, bet_context: Optional[str], history: List[Dict[str, Any]]) -> str:
        """
        Generate a response using GPT.
        
        Args:
            query: The user's query
            bet_context: Formatted betting data context
            history: Chat history
            
        Returns:
            GPT-generated response
        """
        # Format chat history for GPT
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add chat history (up to 10 most recent messages)
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["message"]})
        
        # Add betting context to the user's query if available
        user_content = query
        if bet_context:
            user_content += f"\n\nHere is relevant betting information to help answer the query:\n\n{bet_context}"
            
        # Add the current query
        messages.append({"role": "user", "content": user_content})
        
        # Generate response using GPT
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating GPT response: {str(e)}", exc_info=True)
            return self._generate_fallback_response(query)
