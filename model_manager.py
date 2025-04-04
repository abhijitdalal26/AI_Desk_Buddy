"""
ModelManager - Handles interactions with the Ollama model
"""
import ollama

class ModelManager:
    def __init__(self, model_name="llama3.2:3b"):
        """Initialize the model manager.
        
        Args:
            model_name: Name of the Ollama model to use
        """
        self.model_name = model_name
    
    def generate_stream(self, messages):
        """Generate a streaming response from the model.
        
        Args:
            messages: List of message dictionaries to send to the model
            
        Yields:
            str: Tokens from the model response
        """
        stream = ollama.chat(
            model=self.model_name,
            messages=messages,
            stream=True
        )
        
        for chunk in stream:
            token = chunk["message"]["content"]
            yield token
    
    def generate(self, messages):
        """Generate a complete response from the model.
        
        Args:
            messages: List of message dictionaries to send to the model
            
        Returns:
            str: Complete model response
        """
        response = ollama.chat(
            model=self.model_name,
            messages=messages
        )
        
        return response["message"]["content"]
    
    def test_connection(self):
        """Test the connection to the Ollama service.
        
        Raises:
            Exception: If the connection fails
        """
        ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": "Hello"}]
        )