"""
HistoryService - Handles saving and loading chat history
"""
import json
import os
import uuid
from datetime import datetime

class HistoryService:
    def __init__(self, history_file="chat_history.json"):
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {self.history_file}. Creating new history.")
        return {"sessions": []}
    
    def save_history(self):
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)
    
    def add_session(self, session_messages):
        if not session_messages or all(msg.get("role") == "system" for msg in session_messages):
            return
        session_entry = {
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "messages": [{"timestamp": datetime.now().isoformat(), **msg} for msg in session_messages]
        }
        self.history["sessions"].append(session_entry)
        self.save_history()
    
    def get_all_messages(self):
        all_messages = []
        for session in self.history["sessions"]:
            session_id = session["session_id"]
            for msg in session["messages"]:
                all_messages.append({**msg, "session_id": session_id})
        return all_messages
    
    def get_session_by_id(self, session_id):
        for session in self.history["sessions"]:
            if session["session_id"] == session_id:
                return session
        return None