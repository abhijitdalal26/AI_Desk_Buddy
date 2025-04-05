import time
from datetime import datetime
from real_time_face_recognition.src.face_recognizer import detect_face_once

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
        
        if self.voice_service:
            self.voice_service.start()
        
        self._greet_user_with_face_recognition()

    def _greet_user_with_face_recognition(self):
        name, confidence = detect_face_once(timeout=5.0)
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 12:
            greeting = "Good morning"
        elif 12 <= current_hour < 17:
            greeting = "Good afternoon"
        elif 17 <= current_hour < 22:
            greeting = "Good evening"
        else:
            greeting = "Hello"
        
        if name != "Unknown" and confidence <= 100:
            greeting_message = f"{greeting}, {name}! How can I assist you today?"
        else:
            greeting_message = f"{greeting}! I couldn't recognize you. How can I assist you today?"
        
        self.current_session.append({"role": "assistant", "content": greeting_message})
        print(f"AI: {greeting_message}")
        
        if self.voice_service:
            self.voice_service.speak_token(greeting_message)
            self.voice_service.wait_until_done()

    def run_chat_loop(self):
        print(f"Starting AI Desk Buddy with {self.ollama_service.model_name}.")
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
    
    def _check_pending_tasks(self, show_output=False):
        pending_tasks = self.task_service.get_pending_tasks()
        if pending_tasks and show_output:
            print("\n--- Your pending tasks ---")
            for i, task in enumerate(pending_tasks, 1):
                print(f"{i}. {task['description']}")
            print("-------------------------\n")
            return True
        return False

    def _process_user_message(self, user_input):
        user_message = {"role": "user", "content": user_input}
        self.current_session.append(user_message)
        
        task_info = self.task_service.extract_task(user_input)
        
        augmented_messages = self.context_engine.augment_with_context(self.current_session, user_input)
        
        try:
            print("AI: ", end="", flush=True)
            response_text = ""
            for token in self.ollama_service.generate_stream(augmented_messages):
                token = token.replace("*", "").replace("**", "").replace("`", "")
                print(token, end="", flush=True)
                response_text += token
                if self.voice_service:
                    self.voice_service.speak_token(token)
            print()
            
            if self.voice_service:
                self.voice_service.wait_until_done()
                
            assistant_message = {"role": "assistant", "content": response_text}
            self.current_session.append(assistant_message)
            
            self.context_engine.add_message(user_message)
            self.context_engine.add_message(assistant_message)
            
            # Handle task addition
            if task_info:
                task_id = self.task_service.add_task(
                    description=task_info["description"],
                    due_at=task_info.get("due_at")
                )
                if task_id:
                    print(f"✓ Task added: {task_info['description']}")
            
            # Handle task completion
            if "complete" in user_input.lower() and "task" in user_input.lower():
                for task in self.task_service.get_pending_tasks():
                    if task["description"].lower() in user_input.lower():
                        self.task_service.complete_task(task["task_id"])
                        print(f"✓ Task completed and removed: {task['description']}")
                        break
            
            # Handle reminder requests
            if "remind me" in user_input.lower() or "give me reminders" in user_input.lower():
                if not self._check_pending_tasks(show_output=True):
                    print("AI: You have no pending tasks.")
                    
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