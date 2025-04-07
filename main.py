#!/usr/bin/env python3
"""
AI Desk Buddy - Main Application (Laptop)
"""
from chat_controller import ChatController
from ollama_service import OllamaService
from history_service import HistoryService
from context_engine import ContextEngine
from task_service import TaskService
import socket

def start_server(host='192.168.84.248', port=65432):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")
    conn, addr = server_socket.accept()
    print(f"Connected by {addr}")
    return conn

def main():
    """Main application entry point."""
    model_name = "llama3.2:3b"
    history_file = "chat_history.json"
    embeddings_file = "chat_embeddings.json"
    tasks_file = "tasks.json"
    system_prompt = """
    You are AI Desk Buddy, a helpful assistant. 
    Use the context from previous conversations to provide relevant answers.
    You can help manage tasks and respond to date/time queries accurately.
    When you help with tasks, always acknowledge them clearly.
    """

    # Initialize components
    history_service = HistoryService(history_file)
    ollama_service = OllamaService(model_name)
    context_engine = ContextEngine(history_service, embeddings_file)  # Fixed: Added required argument
    task_service = TaskService(tasks_file)
    
    # Start server for communication with Raspberry Pi
    conn = start_server()
    
    chat_controller = ChatController(
        ollama_service, 
        history_service, 
        context_engine, 
        task_service,
        conn,
        system_prompt,
        use_pi_input=True  # Use Raspberry Pi for input
    )
    
    try:
        chat_controller.run_chat_loop()
    except KeyboardInterrupt:
        print("\nExiting AI Desk Buddy. Goodbye!")
    finally:
        history_service.save_history()
        conn.close()

if __name__ == "__main__":
    main()