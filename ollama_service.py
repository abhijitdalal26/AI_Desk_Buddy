"""
OllamaService - Handles interactions with the Ollama model
"""
import ollama

class OllamaService:
    def __init__(self, model_name="llama3.2:3b"):
        self.model_name = model_name
    
    def generate_stream(self, messages):
        stream = ollama.chat(model=self.model_name, messages=messages, stream=True)
        for chunk in stream:
            token = chunk["message"]["content"]
            yield token
    
    def generate(self, messages):
        response = ollama.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]
    
    def test_connection(self):
        ollama.chat(model=self.model_name, messages=[{"role": "user", "content": "Hello"}])