#!/usr/bin/env python3
"""
AI Desk Buddy - Main Application
Entry point for the chat application with RAG capabilities and task reminders.
"""
from chat_controller import ChatController
from ollama_service import OllamaService
from history_service import HistoryService
from context_engine import ContextEngine
from voice_service_factory import VoiceServiceFactory
from task_service import TaskService

# Hardcode voice engine choice here (edit before running)
VOICE_ENGINE = "gtts"  # Options: "gtts" or "elevenlabs"

def main():
    """Main application entry point."""
    # Core settings
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

    # Voice settings (edit these as needed)
    if VOICE_ENGINE == "gtts":
        voice_params = {
            "voice_engine": "gtts",
            "lang": "en",  # Language for gTTS
            "slow": False  # Slow speech for gTTS
        }
    elif VOICE_ENGINE == "elevenlabs":
        voice_params = {
            "voice_engine": "elevenlabs",
            "elevenlabs_api_key": "YOUR_API_KEY_HERE",  # Replace with your key
            "elevenlabs_voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
            "elevenlabs_model_id": "eleven_monolingual_v1",
            "elevenlabs_stability": 0.5,
            "elevenlabs_similarity_boost": 0.5
        }
    else:
        raise ValueError("VOICE_ENGINE must be 'gtts' or 'elevenlabs'")

    # Initialize components
    history_service = HistoryService(history_file)
    ollama_service = OllamaService(model_name)
    context_engine = ContextEngine(history_service, embeddings_file)
    task_service = TaskService(tasks_file)
    
    # Initialize voice service based on VOICE_ENGINE
    voice_service = VoiceServiceFactory.create(**voice_params)
    
    chat_controller = ChatController(
        ollama_service, 
        history_service, 
        context_engine, 
        task_service,
        voice_service,
        system_prompt
    )
    
    # Run the chat application
    try:
        chat_controller.run_chat_loop()
    except KeyboardInterrupt:
        print("\nExiting AI Desk Buddy. Goodbye!")
    finally:
        history_service.save_history()
        if voice_service:
            voice_service.stop()

if __name__ == "__main__":
    main()