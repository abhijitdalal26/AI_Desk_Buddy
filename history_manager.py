"""
HistoryManager - Handles saving and loading chat history
"""
import json
import os
import uuid
from datetime import datetime

class HistoryManager:
    def __init__(self, history_file="chat_history.json"):
        """Initialize the history manager.
        
        Args:
            history_file: Path to the file where chat history is stored
        """
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self):
        """Load chat history from file.
        
        Returns:
            dict: The loaded chat history structure
        """
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {self.history_file}. Creating new history.")
        
        # Return default structure if file doesn't exist or has invalid format
        return {"sessions": []}
    
    def save_history(self):
        """Save chat history to file."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)
    
    def add_session(self, session_messages):
        """Add a completed session to history.
        
        Args:
            session_messages: List of message dictionaries from the session
        """
        # Skip empty sessions
        if not session_messages or all(msg.get("role") == "system" for msg in session_messages):
            return
        
        # Create a new session entry
        session_entry = {
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "messages": [
                {
                    **msg,
                    "timestamp": datetime.now().isoformat()
                }
                for msg in session_messages
            ]
        }
        
        # Add to history and save
        self.history["sessions"].append(session_entry)
        self.save_history()
    
    def get_all_messages(self):
        """Get all messages from all sessions.
        
        Returns:
            list: All message dictionaries with session metadata
        """
        all_messages = []
        for session in self.history["sessions"]:
            session_id = session["session_id"]
            for msg in session["messages"]:
                # Add session context to each message
                message_with_context = {
                    **msg,
                    "session_id": session_id
                }
                all_messages.append(message_with_context)
        
        return all_messages
    
    def get_session_by_id(self, session_id):
        """Get a specific session by ID.
        
        Args:
            session_id: The UUID of the session to retrieve
            
        Returns:
            dict or None: The session dict if found, None otherwise
        """
        for session in self.history["sessions"]:
            if session["session_id"] == session_id:
                return session
        return None