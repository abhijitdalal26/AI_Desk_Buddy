# TaskService.py
"""
TaskService - Handles task recognition, storage, and management
"""
import os
import json
import uuid
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional, Any

from task_recognizer import TaskRecognizer
from datetime_utils import DateTimeUtility

class TaskService:
    def __init__(self, tasks_file="tasks.json"):
        self.tasks_file = tasks_file
        self.tasks = self._load_tasks()
        self.task_recognizer = TaskRecognizer()
        self.datetime_util = DateTimeUtility()
    
    def _load_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {self.tasks_file}. Creating new tasks file.")
        return {"tasks": []}
    
    def _save_tasks(self):
        with open(self.tasks_file, "w") as f:
            json.dump(self.tasks, f, indent=2)
    
    def extract_task(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Extract task information from user input"""
        # Simplified to trigger on 'task' keyword
        if "task" in user_input.lower():
            description = user_input.replace("task", "").strip()
            return {"description": description, "due_at": None}
        return self.task_recognizer.extract_task(user_input)
    
    def add_task(self, description: str, due_at: Optional[str] = None, 
                session_id: Optional[str] = None) -> str:
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        if due_at:
            task["due_at"] = due_at
        
        if session_id:
            task["session_id"] = session_id
            
        self.tasks["tasks"].append(task)  # Simply append new task
        self._save_tasks()
        return task_id
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        for i, task in enumerate(self.tasks["tasks"]):
            if task["task_id"] == task_id:
                for key, value in kwargs.items():
                    task[key] = value
                self._save_tasks()
                return True
        return False
    
    def complete_task(self, task_id: str) -> bool:
        # Instead of just marking as completed, remove the task
        for i, task in enumerate(self.tasks["tasks"]):
            if task["task_id"] == task_id:
                self.tasks["tasks"].pop(i)
                self._save_tasks()
                return True
        return False
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        for task in self.tasks["tasks"]:
            if task["task_id"] == task_id:
                return task
        return None
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        return [task for task in self.tasks["tasks"] if task["status"] == status]
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        pending = self.get_tasks_by_status("pending")
        return sorted(pending, key=lambda x: x.get("due_at", "9999"))
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        now = datetime.now().isoformat()
        return [
            task for task in self.get_pending_tasks() 
            if "due_at" in task and task["due_at"] < now
        ]
    
    def delete_task(self, task_id: str) -> bool:
        for i, task in enumerate(self.tasks["tasks"]):
            if task["task_id"] == task_id:
                self.tasks["tasks"].pop(i)
                self._save_tasks()
                return True
        return False
    
    def handle_date_query(self, query: str) -> str:
        return self.datetime_util.process_date_query(query)