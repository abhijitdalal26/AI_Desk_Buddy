# chat_controller.py
import time
from datetime import datetime
from real_time_face_recognition.src.face_recognizer import detect_face_once  # Assuming package structure

class ChatController:
    def __init__(self, ollama_service, history_service, context_engine, 
                 task_service, voice_service=None, system_prompt=None):
        self.ollama_service = ollama_service
        self.history_service = history_service
        self.context_engine = context_engine
        self.task_service = task_service
        self.voice_service = voice_service
        self.current_session = []
        if system_prompt:
            self.current_session.append({"role": "system", "content": system_prompt})
        
        # Start voice service immediately if present
        if self.voice_service:
            self.voice_service.start()
        
        # Detect face and greet user at startup
        self._greet_user_with_face_recognition()

    def _greet_user_with_face_recognition(self):
        """Detect the user's face and generate a personalized greeting."""
        name, confidence = detect_face_once(timeout=5.0)  # Explicitly set 5-second timeout
        current_hour = datetime.now().hour
        
        # Determine greeting based on time of day
        if 5 <= current_hour < 12:
            greeting = "Good morning"
        elif 12 <= current_hour < 17:
            greeting = "Good afternoon"
        elif 17 <= current_hour < 22:
            greeting = "Good evening"
        else:
            greeting = "Hello"
        
        # Craft greeting message
        if name != "Unknown" and confidence <= 100:
            greeting_message = f"{greeting}, {name}! How can I assist you today?"
        else:
            greeting_message = f"{greeting}! I couldn't recognize you. How can I assist you today?"
        
        # Add greeting to session and display it
        self.current_session.append({"role": "assistant", "content": greeting_message})
        print(f"AI: {greeting_message}")
        
        if self.voice_service:
            self.voice_service.speak_token(greeting_message)  # Use speak_token instead of speak
            self.voice_service.wait_until_done()

    def run_chat_loop(self):
        print(f"Starting AI Desk Buddy with {self.ollama_service.model_name}.")
        # voice_service.start() removed from here since it's in __init__
        
        # Check for pending tasks at session start
        self._check_pending_tasks()
        
        print("Type your message (or 'exit' to quit):")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                self.history_service.add_session(self.current_session)
                if self.voice_service:
                    self.voice_service.stop()
                print("Shutting down AI Desk Buddy.")
                break
            self._process_user_message(user_input)
    
    def _check_pending_tasks(self):
        """Check for pending tasks and inform the user at the start of a session"""
        pending_tasks = self.task_service.get_pending_tasks()
        if pending_tasks:
            print("\n--- You have pending tasks ---")
            for i, task in enumerate(pending_tasks, 1):
                due_str = ""
                if task.get("due_at"):
                    due_date = datetime.fromisoformat(task["due_at"])
                    due_str = f" - Due: {due_date.strftime('%Y-%m-%d %H:%M')}"
                print(f"{i}. {task['description']}{due_str}")
            print("-----------------------------\n")
            
            # Add pending tasks to the conversation context
            task_list = "\n".join([f"- {task['description']}" for task in pending_tasks])
            task_message = {
                "role": "system", 
                "content": f"The user has the following pending tasks:\n{task_list}\n"
            }
            if len(self.current_session) > 0 and self.current_session[0]["role"] == "system":
                # Insert after the first system message
                self.current_session.insert(1, task_message)
            else:
                self.current_session.insert(0, task_message)
    
    def _process_user_message(self, user_input):
        user_message = {"role": "user", "content": user_input}
        self.current_session.append(user_message)
        
        # Check for task-related content and extract if present
        task_info = self.task_service.extract_task(user_input)
        
        # Augment messages with relevant context from history
        augmented_messages = self.context_engine.augment_with_context(self.current_session, user_input)
        
        try:
            print("AI: ", end="", flush=True)
            response_text = ""
            for token in self.ollama_service.generate_stream(augmented_messages):
                print(token, end="", flush=True)
                response_text += token
                if self.voice_service:
                    self.voice_service.speak_token(token)
            print()
            
            if self.voice_service:
                self.voice_service.wait_until_done()
                
            assistant_message = {"role": "assistant", "content": response_text}
            self.current_session.append(assistant_message)
            
            # Add messages to context engine
            self.context_engine.add_message(user_message)
            self.context_engine.add_message(assistant_message)
            
            # Process and save the task if one was detected
            if task_info:
                task_id = self.task_service.add_task(
                    description=task_info["description"],
                    due_at=task_info.get("due_at")
                )
                if task_id:
                    print(f"✓ Task added: {task_info['description']}")
                    
        except Exception as e:
            print(f"\nError: {e}")
            self._attempt_recovery()
    
    def _attempt_recovery(self):
        try:
            print("Attempting to recover connection...")
            self.ollama_service.test_connection()
            print("Connection recovered.")
        except:
            print("Recovery failed. The Ollama service may need to be restarted.")