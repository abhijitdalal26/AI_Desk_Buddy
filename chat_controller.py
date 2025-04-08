import time
from datetime import datetime
import re
import socket

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
    def __init__(self, ollama_service, deepseek_service, history_service, context_engine, 
                 task_service, conn, system_prompt=None, use_pi_input=True):
        # Initialize with both Ollama and DeepSeek services
        self.ollama_service = ollama_service
        self.deepseek_service = deepseek_service
        self.history_service = history_service
        self.context_engine = context_engine
        self.task_service = task_service
        self.conn = conn
        self.use_pi_input = use_pi_input
        self.current_session = []
        self.current_service = ollama_service  # Default to local Ollama
        if system_prompt:
            self.current_session.append({"role": "system", "content": system_prompt})
        
        self._greet_user_with_face_recognition()

    def _greet_user_with_face_recognition(self):
        try:
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
                # Send the TTS_END signal to complete the greeting
                self.conn.sendall("TTS_END:".encode())
        except Exception as e:
            print(f"Error in greeting: {e}")
            # Continue even if greeting fails

    def run_chat_loop(self):
        # Start with the current service's model name
        print(f"Starting AI Desk Buddy with {self.current_service.model_name}.")
        self._check_pending_tasks()
        
        if self.use_pi_input:
            print("Waiting for input from Raspberry Pi...")
            while True:
                try:
                    data = self.conn.recv(1024).decode()
                    if data.startswith("INPUT:"):
                        user_input = data.split(":", 1)[1].strip()
                        if user_input.lower() in ["exit", "quit", "bye"] or "ok bye" in user_input.lower():
                            self.history_service.add_session(self.current_session)
                            self.conn.sendall("EXIT:".encode())
                            print("Shutting down AI Desk Buddy.")
                            break
                        print(f"You: {user_input}")
                        self._process_user_message(user_input)
                except socket.timeout:
                    # Just a timeout, continue waiting
                    continue
                except ConnectionResetError:
                    print("Connection was reset. Shutting down.")
                    break
                except Exception as e:
                    print(f"Error receiving input: {e}")
                    time.sleep(1)  # Brief pause before trying again
        else:
            print("Type your message (or 'exit' to quit):")
            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in ["exit", "quit", "bye"] or "ok bye" in user_input.lower():
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

    def _send_message_with_end(self, message):
        """Helper method to send a message followed by the TTS_END signal"""
        try:
            print(f"AI: {message}")
            self.conn.sendall(f"TTS:{message}".encode())
            self.conn.sendall("TTS_END:".encode())
        except Exception as e:
            print(f"Error sending message: {e}")

    def _get_user_confirmation(self, timeout=30):
        """Get user confirmation with improved timeout handling"""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                data = self.conn.recv(1024).decode()
                if data.startswith("INPUT:"):
                    response = data.split(":", 1)[1].strip().lower()
                    print(f"You: {response}")
                    self.current_session.append({"role": "user", "content": response})
                    if response in ["yes", "no"]:
                        return response
                    else:
                        self._send_message_with_end("Please respond with 'yes' or 'no'.")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error receiving confirmation: {e}")
                return "error"
        
        # If we get here, we timed out
        self._send_message_with_end("No response received within the timeout period. Keeping current model.")
        return "timeout"

    def _switch_to_cloud(self):
        try:
            # First, test the cloud connection before prompting user
            print("Testing DeepSeek cloud connection...")
            if not self.deepseek_service.test_connection():
                error_message = "Cannot connect to DeepSeek cloud service. Please check your API key and internet connection."
                self._send_message_with_end(error_message)
                self.current_session.append({"role": "assistant", "content": error_message})
                return
                
            # Prompt user to confirm switching to DeepSeek
            confirm_message = "I'd like to switch to DeepSeek cloud LLM for better capabilities. Confirm with 'yes' or 'no'."
            self._send_message_with_end(confirm_message)
            self.current_session.append({"role": "assistant", "content": confirm_message})
            
            # Wait for user confirmation with timeout
            response = self._get_user_confirmation()
            
            if response == "yes":
                self.current_service = self.deepseek_service
                success_message = "Switched to DeepSeek cloud LLM. You now have access to enhanced capabilities."
                self._send_message_with_end(success_message)
                self.current_session.append({"role": "assistant", "content": success_message})
            elif response == "no":
                cancel_message = "Staying with local LLM as requested."
                self._send_message_with_end(cancel_message)
                self.current_session.append({"role": "assistant", "content": cancel_message})
            else:
                invalid_message = "Switch canceled due to invalid response or timeout. Please try again if you still want to switch."
                self._send_message_with_end(invalid_message)
                self.current_session.append({"role": "assistant", "content": invalid_message})
        except Exception as e:
            error_message = f"Error while trying to switch models: {str(e)}"
            self._send_message_with_end(error_message)
            print(f"Error in switch_to_cloud: {e}")

    def _switch_to_local(self):
        try:
            # Test local connection first
            print("Testing local Ollama connection...")
            if not self.ollama_service.test_connection():
                error_message = "Cannot connect to local Ollama service. Please check if it's running."
                self._send_message_with_end(error_message)
                self.current_session.append({"role": "assistant", "content": error_message})
                return
                
            # Prompt user to confirm switching to Ollama
            confirm_message = "I'd like to switch back to local LLM. This may reduce capabilities but provide faster responses. Confirm with 'yes' or 'no'."
            self._send_message_with_end(confirm_message)
            self.current_session.append({"role": "assistant", "content": confirm_message})
            
            # Wait for user confirmation with timeout
            response = self._get_user_confirmation()
            
            if response == "yes":
                self.current_service = self.ollama_service
                success_message = "Switched back to local LLM."
                self._send_message_with_end(success_message)
                self.current_session.append({"role": "assistant", "content": success_message})
            elif response == "no":
                cancel_message = "Staying with DeepSeek cloud LLM as requested."
                self._send_message_with_end(cancel_message)
                self.current_session.append({"role": "assistant", "content": cancel_message})
            else:
                invalid_message = "Switch canceled due to invalid response or timeout. Please try again if you still want to switch."
                self._send_message_with_end(invalid_message)
                self.current_session.append({"role": "assistant", "content": invalid_message})
        except Exception as e:
            error_message = f"Error while trying to switch models: {str(e)}"
            self._send_message_with_end(error_message)
            print(f"Error in switch_to_local: {e}")

    def _process_user_message(self, user_input):
        user_input_lower = user_input.lower()
        # Handle switching commands before processing regular messages
        if user_input_lower == "switch to cloud" and self.current_service == self.ollama_service:
            self._switch_to_cloud()
            return
        elif user_input_lower == "switch to local" and self.current_service == self.deepseek_service:
            self._switch_to_local()
            return
        
        user_message = {"role": "user", "content": user_input}
        self.current_session.append(user_message)
        
        task_info = self.task_service.extract_task(user_input)
        augmented_messages = self.context_engine.augment_with_context(self.current_session, user_input)
        
        try:
            print("AI: ", end="", flush=True)
            response_text = ""
            tokens_received = 0
            last_update_time = time.time()
            
            # Use the current service (Ollama or DeepSeek) to generate response
            for token in self.current_service.generate_stream(augmented_messages):
                current_time = time.time()
                tokens_received += 1
                
                # Periodically log status for long responses
                if tokens_received % 100 == 0:
                    print(f"\n[Received {tokens_received} tokens]", end="", flush=True)
                
                # Check for long pauses between tokens
                if current_time - last_update_time > 5.0 and tokens_received > 1:
                    print(f"\n[Long pause detected ({current_time - last_update_time:.1f}s)]", end="", flush=True)
                
                last_update_time = current_time
                clean_token = strip_markdown(token)
                
                if response_text and not response_text.endswith(" ") and not clean_token.startswith(" "):
                    print(" ", end="", flush=True)
                    response_text += " "
                    
                print(clean_token, end="", flush=True)
                response_text += clean_token
                
                try:
                    self.conn.sendall(f"TTS:{clean_token}".encode())  # Send each token
                except Exception as e:
                    print(f"\n[Error sending token: {e}]", end="", flush=True)
                    # Continue even if sending fails
            
            print()  # Newline after response
            
            try:
                self.conn.sendall("TTS_END:".encode())  # Signal the end of the response
            except Exception as e:
                print(f"Error sending TTS_END: {e}")
            
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
            print(f"\nError generating response: {e}")
            error_message = f"Sorry, I encountered an error while generating a response: {str(e)}"
            self._send_message_with_end(error_message)
            self._attempt_recovery()
    
    def _attempt_recovery(self):
        try:
            print("Attempting to recover connection...")
            recovered = False
            
            # Try current service first
            if self.current_service.test_connection():
                recovered = True
                print("Connection to current service recovered.")
            else:
                # If current service fails, try the alternative service
                alternative_service = self.ollama_service if self.current_service == self.deepseek_service else self.deepseek_service
                print(f"Trying alternative service ({alternative_service.model_name})...")
                if alternative_service.test_connection():
                    self.current_service = alternative_service
                    recovered = True
                    recovery_message = f"Switched to {alternative_service.model_name} due to connection issues."
                    self._send_message_with_end(recovery_message)
                    print("Switched to alternative service.")
            
            if not recovered:
                recovery_message = "I'm having trouble with both LLM services. Please check your connections and restart if necessary."
                self._send_message_with_end(recovery_message)
                print("Failed to recover using either service.")
        except Exception as e:
            print(f"Recovery attempt failed: {e}")
            recovery_message = "I'm having trouble with my connection. Please try again or restart me."
            self._send_message_with_end(recovery_message)
            print("The active LLM service may need to be restarted.")