import requests
from sseclient import SSEClient
import json
import time
import os

class DeepSeekService:
    def __init__(self, api_key, model_name="deepseek-chat"):
        # Store API key and model name, set base URL for DeepSeek API
        self.api_key = api_key.strip() if api_key else ""
        self.model_name = model_name
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.last_error = None
        
        # Diagnostics - print API key info (first 4 chars only for security)
        if self.api_key:
            print(f"DeepSeek API key loaded: {self.api_key[:4]}...{self.api_key[-4:]} ({len(self.api_key)} chars)")
        else:
            print("WARNING: DeepSeek API key not set or empty")

    def generate_stream(self, messages):
        # Ensure we have a valid API key
        if not self.api_key:
            self.last_error = "No API key configured"
            yield "I cannot access the cloud model because no API key is configured. Please check your config.env file."
            return

        # Prepare headers with API key and JSON content type
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Format payload with messages, enable streaming
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "temperature": 0.7  # Controls creativity (0-1)
        }
        
        try:
            print(f"Connecting to DeepSeek API at {self.base_url}...")
            # Send POST request with streaming enabled
            response = requests.post(
                self.base_url, 
                headers=headers, 
                json=payload, 
                stream=True,
                timeout=45  # Increased timeout to prevent hanging
            )
            
            # Check if request was successful
            if response.status_code != 200:
                error_data = None
                try:
                    error_data = response.json()
                    print(f"DeepSeek API error response: {error_data}")
                except:
                    error_data = {"error": f"HTTP status {response.status_code}"}
                    print(f"DeepSeek API error: HTTP {response.status_code}")
                
                error_message = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                self.last_error = error_message
                yield f" [Error: {error_message}] "
                return
            
            # Parse SSE stream
            client = SSEClient(response)
            tokens_received = 0
            
            for event in client.events():
                if event.event == "message":
                    try:
                        data = json.loads(event.data)
                        if "choices" in data and data["choices"]:
                            token = data["choices"][0]["delta"].get("content", "")
                            if token:  # Yield non-empty tokens
                                tokens_received += 1
                                yield token
                                
                            # Check if we're at the end
                            if data.get("choices", [{}])[0].get("finish_reason") == "stop":
                                break
                    except json.JSONDecodeError:
                        yield " [Error parsing response] "
                    except Exception as e:
                        yield f" [Stream error: {str(e)}] "
                        
            # Verify we got a valid response
            if tokens_received == 0:
                yield " [No response content received from cloud service] "
                
        except requests.exceptions.Timeout:
            self.last_error = "Request timed out"
            yield " [DeepSeek request timed out. The service might be busy.] "
        except requests.exceptions.RequestException as e:
            self.last_error = str(e)
            yield f" [Error connecting to DeepSeek: {str(e)}] "
        except Exception as e:
            self.last_error = str(e)
            yield f" [Unexpected error: {str(e)}] "

    def generate(self, messages):
        # Non-streaming version for full response
        if not self.api_key:
            self.last_error = "No API key configured"
            return "I cannot access the cloud model because no API key is configured. Please check your config.env file."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.base_url, 
                headers=headers, 
                json=payload,
                timeout=45  # Increased timeout
            )
            
            if response.status_code != 200:
                error_data = None
                try:
                    error_data = response.json()
                except:
                    error_data = {"error": f"HTTP status {response.status_code}"}
                
                error_message = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                self.last_error = error_message
                return f"Error from DeepSeek API: {error_message}"
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            self.last_error = "Request timed out"
            return "DeepSeek request timed out. The service might be busy."
        except requests.exceptions.RequestException as e:
            self.last_error = str(e)
            return f"Error connecting to DeepSeek: {str(e)}"
        except Exception as e:
            self.last_error = str(e)
            return f"Unexpected error: {str(e)}"

    def test_connection(self):
        """Test API connection with improved error handling"""
        if not self.api_key:
            print("DeepSeek test connection failed: No API key configured")
            self.last_error = "No API key configured"
            return False
            
        try:
            print(f"Testing DeepSeek connection with API key: {self.api_key[:4]}...{self.api_key[-4:]}")
            # Send a small test query with short timeout
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
                "max_tokens": 5,  # Limit response size for quick test
                "temperature": 0.7
            }
            
            # Use a short timeout for the connection test
            response = requests.post(
                self.base_url, 
                headers=headers, 
                json=payload,
                timeout=10
            )
            
            print(f"DeepSeek test response status: {response.status_code}")
            
            if response.status_code != 200:
                error_data = None
                try:
                    error_data = response.json()
                    print(f"DeepSeek API error response: {error_data}")
                except:
                    error_data = {"error": f"HTTP status {response.status_code}"}
                
                error_message = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                self.last_error = error_message
                print(f"DeepSeek test connection failed: {error_message}")
                return False
                
            # If we got here, the connection is good
            print("DeepSeek test connection successful")
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"DeepSeek test connection failed: {e}")
            return False