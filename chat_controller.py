import time
from datetime import datetime
import re

def strip_markdown(text):
    """Remove common Markdown formatting from text."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text.strip()

class ChatController:
    def __init__(self, ollama_service, history_service, context_engine, 
                 task_service, conn, system_prompt=None, use_pi_input=True):
        self.ollama_service = ollama_service
        self.history_service = history_service
        self.context_engine = context_engine
        self.task_service = task_service
        self.conn = conn
        self.use_pi_input = use_pi_input
        self.current_session = []
        if system_prompt:
            self.current_session.append({"role": "system", "content": system_prompt})
        
        self._greet_user_with_face_recognition()

    def _greet_user_with_face_recognition(self):
        data = self.conn.recv(1024).decode()
        if data.startswith("NAME:"):
            name = data.split(":")[1]
            current_hour = datetime.now().hour
            
            if 5 <= current_hour < 12:
                greeting = "Good morning"
            elif 12 <= current_hour < 17:
                greeting = "Good afternoon"
            elif 17 <= current_hour < 22:
                greeting = "Good evening"
            else:
                greeting = "Hello"
            
            if name != "Unknown":
                greeting_message = f"{greeting}, {name}! How can I assist you today?"
            else:
                greeting_message = f"{greeting}! I couldn't recognize you. How can I assist you today?"
            
            self.current_session.append({"role": "assistant", "content": greeting_message})
            print(f"AI: {greeting_message}")
            self.conn.sendall(f"TTS:{greeting_message}".encode())

    def run_chat_loop(self):
        print(f"Starting AI Desk Buddy with {self.ollama_service.model_name}.")
        self._check_pending_tasks()
        
        if self.use_pi_input:
            print("Waiting for input from Raspberry Pi...")
            while True:
                data = self.conn.recv(1024).decode()
                if data.startswith("INPUT:"):
                    user_input = data.split(":", 1)[1].strip()
                    if user_input.lower() in ["exit", "quit"]:
                        self.history_service.add_session(self.current_session)
                        self.conn.sendall("EXIT:".encode())
                        print("Shutting down AI Desk Buddy.")
                        break
                    print(f"You: {user_input}")
                    self._process_user_message(user_input)
        else:
            print("Type your message (or 'exit' to quit):")
            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in ["exit", "quit"]:
                    self.history_service.add_session(self.current_session)
                    self.conn.sendall("EXIT:".encode())
                    print("Shutting down AI Desk Buddy.")
                    break
                self._process_user_message(user_input)

    def _check_pending_tasks(self):
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
            
            task_list = "\n".join([f"- {task['description']}" for task in pending_tasks])
            task_message = {
                "role": "system", 
                "content": f"The user has the following pending tasks:\n{task_list}\n"
            }
            if len(self.current_session) > 0 and self.current_session[0]["role"] == "system":
                self.current_session.insert(1, task_message)
            else:
                self.current_session.insert(0, task_message)
    
    def _process_user_message(self, user_input):
        user_message = {"role": "user", "content": user_input}
        self.current_session.append(user_message)
        
        task_info = self.task_service.extract_task(user_input)
        augmented_messages = self.context_engine.augment_with_context(self.current_session, user_input)
        
        try:
            print("AI: ", end="", flush=True)
            response_text = ""
            for token in self.ollama_service.generate_stream(augmented_messages):
                clean_token = strip_markdown(token)
                if response_text and not response_text.endswith(" ") and not clean_token.startswith(" "):
                    print(" ", end="", flush=True)
                print(clean_token, end="", flush=True)
                response_text += clean_token
                self.conn.sendall(f"TTS:{clean_token}".encode())  # Send each token
            print()  # Newline after response
            self.conn.sendall("TTS_END:".encode())  # Signal the end of the response
            
            assistant_message = {"role": "assistant", "content": response_text}
            self.current_session.append(assistant_message)
            
            self.context_engine.add_message(user_message)
            self.context_engine.add_message(assistant_message)
            
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