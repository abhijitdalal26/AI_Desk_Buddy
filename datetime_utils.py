"""
DateTimeUtility - Provides date and time utilities for the application
"""
import re
from datetime import datetime, timedelta
from typing import Optional

class DateTimeUtility:
    def __init__(self):
        self.weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2, 
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
    
    def get_current_date(self) -> str:
        """Get the current date as a string"""
        return datetime.now().strftime("%A, %B %d, %Y")
    
    def get_current_time(self) -> str:
        """Get the current time as a string"""
        return datetime.now().strftime("%I:%M %p")
    
    def get_current_datetime(self) -> str:
        """Get the current date and time as a string"""
        return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    def parse_time_reference(self, time_ref: str) -> Optional[str]:
        """
        Parse a time reference into an ISO datetime string
        
        Parameters:
        - time_ref: A string like "tomorrow", "next week", "in 3 days", etc.
        
        Returns:
        - ISO-formatted datetime string or None if parsing failed
        """
        now = datetime.now()
        time_ref = time_ref.lower()
        
        # Handle specific time references
        if "today" in time_ref:
            return now.replace(hour=23, minute=59, second=59).isoformat()
        
        if "tomorrow" in time_ref:
            return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()
        
        if "next week" in time_ref:
            return (now + timedelta(days=7)).isoformat()
        
        if "next month" in time_ref:
            # Simple approximation, not handling month boundaries perfectly
            return (now + timedelta(days=30)).isoformat()
        
        # Handle weekdays
        for day, offset in self.weekdays.items():
            if day in time_ref:
                current_weekday = now.weekday()
                days_until = (offset - current_weekday) % 7
                if days_until == 0:  # If it's the same day, assume next week
                    days_until = 7
                target_date = now + timedelta(days=days_until)
                return target_date.replace(hour=9, minute=0, second=0).isoformat()
        
        # Handle "in X time" patterns
        in_match = re.search(r"in\s+(\d+)\s+(minute|hour|day|week|month)s?", time_ref)
        if in_match:
            amount = int(in_match.group(1))
            unit = in_match.group(2)
            
            if unit == "minute":
                return (now + timedelta(minutes=amount)).isoformat()
            elif unit == "hour":
                return (now + timedelta(hours=amount)).isoformat()
            elif unit == "day":
                return (now + timedelta(days=amount)).isoformat()
            elif unit == "week":
                return (now + timedelta(weeks=amount)).isoformat()
            elif unit == "month":
                # Simple approximation
                return (now + timedelta(days=30*amount)).isoformat()
        
        # Handle specific times
        time_match = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_ref)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            
            return now.replace(hour=hour, minute=minute, second=0).isoformat()
        
        # Handle dates in format MM/DD
        date_match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", time_ref)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            year = int(date_match.group(3)) if date_match.group(3) else now.year
            
            if year < 100:  # Convert 2-digit year to 4-digit
                year += 2000
            
            try:
                return datetime(year, month, day, 9, 0, 0).isoformat()
            except ValueError:
                # Invalid date
                return None
        
        return None
    
    def process_date_query(self, query: str) -> str:
        """
        Process a date-related query and return a response
        
        Parameters:
        - query: The user's query
        
        Returns:
        - A response with the requested date/time information
        """
        query = query.lower()
        
        if "time" in query and "date" in query:
            return f"The current date and time is {self.get_current_datetime()}"
        elif "time" in query:
            return f"The current time is {self.get_current_time()}"
        elif "date" in query or "day" in query or "today" in query:
            return f"Today is {self.get_current_date()}"
        else:
            return f"Today is {self.get_current_date()} and the current time is {self.get_current_time()}"