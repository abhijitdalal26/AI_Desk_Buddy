"""
TaskRecognizer - Recognizes tasks in user inputs using pattern matching
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from datetime_utils import DateTimeUtility

class TaskRecognizer:
    def __init__(self):
        self.datetime_util = DateTimeUtility()
        
        # Task recognition patterns
        self.task_patterns = [
            # "Remind me to..." patterns
            r"remind\s+me\s+to\s+(.+?)(?:\s+by\s+|\s+on\s+|\s+at\s+|\s+in\s+|$)(.+)?",
            r"set\s+(?:a|an)?\s*reminder\s+(?:to|for)\s+(.+?)(?:\s+by\s+|\s+on\s+|\s+at\s+|\s+in\s+|$)(.+)?",
            r"add\s+(?:a|an)?\s*task\s+(?:to|for)\s+(.+?)(?:\s+by\s+|\s+on\s+|\s+at\s+|\s+in\s+|$)(.+)?",
            r"add\s+(?:to\s+)?(?:my\s+)?(?:task\s+)?list\s*[:-]?\s*(.+?)(?:\s+by\s+|\s+on\s+|\s+at\s+|\s+in\s+|$)(.+)?",
            r"I\s+need\s+to\s+(.+?)(?:\s+by\s+|\s+on\s+|\s+at\s+|\s+in\s+|$)(.+)?",
            r"Don't\s+(?:let\s+me\s+)?forget\s+to\s+(.+?)(?:\s+by\s+|\s+on\s+|\s+at\s+|\s+in\s+|$)(.+)?",
        ]
    
    def extract_task(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract task information from text
        
        Parameters:
        - text: User input text
        
        Returns:
        - Dictionary with task info or None if no task was recognized
        """
        for pattern in self.task_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                task_desc = match.group(1).strip()
                due_at = None
                
                # If there's a time/date reference in the second group
                if match.lastindex > 1 and match.group(2):
                    time_ref = match.group(2).strip()
                    due_at = self.datetime_util.parse_time_reference(time_ref)
                
                # Or if there's a time reference in the rest of the text
                elif not due_at:
                    # Look for time references in the entire text
                    time_words = [
                        "today", "tomorrow", "next week", "next month",
                        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                        "in an hour", "in a day", "in a week"
                    ]
                    for word in time_words:
                        if word in text.lower():
                            due_at = self.datetime_util.parse_time_reference(word)
                            break
                
                return {
                    "description": task_desc,
                    "due_at": due_at
                }
        
        return None