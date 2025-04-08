"""
OllamaService - Handles interactions with the Ollama model
"""
import ollama
import time

class OllamaService:
    def __init__(self, model_name="llama3.2:3b"):
        self.model_name = model_name
        self.last_error = None
    
    def generate_stream(self, messages):
        try:
            stream = ollama.chat(model=self.model_name, messages=messages, stream=True)
            tokens_received = 0
            
            for chunk in stream:
                tokens_received += 1
                token = chunk["message"]["content"]
                yield token
                
            if tokens_received == 0:
                self.last_error = "No tokens received"
                yield "[No response content received from local model]"
                
        except Exception as e:
            self.last_error = str(e)
            yield f"[Error with Ollama: {str(e)}]"
    
    def generate(self, messages):
        try:
            response = ollama.chat(model=self.model_name, messages=messages)
            return response["message"]["content"]
        except Exception as e:
            self.last_error = str(e)
            return f"Error with Ollama: {str(e)}"
    
    def test_connection(self):
        """Test connection to Ollama server"""
        try:
            # Try a simple query to see if Ollama is responsive
            ollama.chat(
                model=self.model_name, 
                messages=[{"role": "user", "content": "Hi"}],
                options={"num_predict": 1}  # Limit to a single token for speed
            )
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"Ollama test connection failed: {e}")
            return False