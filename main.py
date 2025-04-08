from chat_controller import ChatController
from ollama_service import OllamaService
from deepseek_service import DeepSeekService
from history_service import HistoryService
from context_engine import ContextEngine
from task_service import TaskService
import socket
import os
from dotenv import load_dotenv  # Import python-dotenv

def start_server(host='192.168.143.248', port=65432):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Add socket option to reuse address
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")
    conn, addr = server_socket.accept()
    print(f"Connected by {addr}")
    # Set a timeout to make socket operations non-blocking
    timeout = float(os.environ.get('SOCKET_TIMEOUT', '60.0'))
    conn.settimeout(timeout)  # Use configured timeout
    return conn, server_socket

def main():
    # Load environment variables from config.env
    load_dotenv('config.env')  # Specify the file name explicitly
    
    # Print loaded configuration for debugging
    print("Configuration loaded from config.env:")
    print(f"- MODEL_NAME: {os.environ.get('MODEL_NAME', 'gemma')}")
    print(f"- DEEPSEEK_MODEL: {os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')}")
    print(f"- DEEPSEEK_API_KEY: {'[SET]' if os.environ.get('DEEPSEEK_API_KEY') else '[NOT SET]'}")
    
    # Retrieve configuration from environment
    model_name = os.environ.get('MODEL_NAME', 'gemma')
    history_file = os.environ.get('HISTORY_FILE', 'chat_history.json')
    embeddings_file = os.environ.get('EMBEDDINGS_FILE', 'embeddings.pkl')
    tasks_file = os.environ.get('TASKS_FILE', 'tasks.json')
    deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    deepseek_model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
    system_prompt = """
    You are AI Desk Buddy, a helpful assistant. 
    Use the context from previous conversations to provide relevant answers.
    You can help manage tasks and respond to date/time queries accurately.
    When you help with tasks, always acknowledge them clearly.
    When using the DeepSeek cloud model, you have more capabilities and can provide more detailed responses.
    """

    # Initialize services
    history_service = HistoryService(history_file)
    ollama_service = OllamaService(model_name)
    deepseek_service = DeepSeekService(deepseek_api_key, deepseek_model)
    context_engine = ContextEngine(history_service, embeddings_file)
    task_service = TaskService(tasks_file)
    
    # Test Ollama connection
    print("Testing Ollama connection...")
    if ollama_service.test_connection():
        print("✓ Ollama connection successful")
    else:
        print("⚠ Ollama connection failed. Check if Ollama is running.")
    
    # Test DeepSeek connection
    print("Testing DeepSeek connection...")
    if deepseek_service.test_connection():
        print("✓ DeepSeek connection successful")
    else:
        print("⚠ DeepSeek connection failed. Check your API key and internet connection.")
    
    conn, server_socket = start_server()
    
    chat_controller = ChatController(
        ollama_service=ollama_service,
        deepseek_service=deepseek_service,
        history_service=history_service,
        context_engine=context_engine,
        task_service=task_service,
        conn=conn,
        system_prompt=system_prompt,
        use_pi_input=True
    )
    
    try:
        chat_controller.run_chat_loop()
    except KeyboardInterrupt:
        print("\nExiting AI Desk Buddy. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        history_service.save_history()
        conn.close()
        server_socket.close()  # Also close the server socket
        print("All connections closed. Goodbye!")

if __name__ == "__main__":
    main()