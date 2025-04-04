#!/usr/bin/env python3
"""
AI Desk Buddy - Main Application
Entry point for the chat application with RAG capabilities.
"""
import argparse
from chat_manager import ChatManager
from model_manager import ModelManager
from history_manager import HistoryManager
from simple_rag_engine import SimpleRAGEngine
from voice_manager import VoiceManager

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='AI Desk Buddy with RAG capabilities')
    parser.add_argument('--model', default='llama3.2:3b', help='Model name to use with Ollama')
    parser.add_argument('--history-file', default='chat_history.json', help='File to store chat history')
    parser.add_argument('--embeddings-file', default='chat_embeddings.json', help='File to store embeddings')
    parser.add_argument('--system-prompt', 
                        default='You are AI Desk Buddy, a helpful assistant. Use the context from previous conversations to provide relevant answers.',
                        help='System prompt for the model')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice output')
    parser.add_argument('--lang', default='en', help='Language code for text-to-speech')
    parser.add_argument('--slow', action='store_true', help='Speak more slowly')
    return parser.parse_args()

def main():
    """Main application entry point."""
    args = parse_arguments()
    
    # Initialize components
    history_manager = HistoryManager(args.history_file)
    model_manager = ModelManager(args.model)
    rag_engine = SimpleRAGEngine(history_manager, args.embeddings_file)
    
    # Initialize voice manager unless explicitly disabled
    voice_manager = None
    if not args.no_voice:
        voice_manager = VoiceManager(lang=args.lang, slow=args.slow)
    
    chat_manager = ChatManager(
        model_manager, 
        history_manager, 
        rag_engine, 
        voice_manager,
        args.system_prompt
    )
    
    # Run the chat application
    try:
        chat_manager.run_chat_loop()
    except KeyboardInterrupt:
        print("\nExiting AI Desk Buddy. Goodbye!")
    finally:
        # Save any pending changes
        history_manager.save_history()
        
        # Stop voice manager if active
        if voice_manager:
            voice_manager.stop()

if __name__ == "__main__":
    main()