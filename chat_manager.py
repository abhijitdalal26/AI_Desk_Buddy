"""
ChatManager - Handles the chat interface and interaction flow
"""
class ChatManager:
    def __init__(self, model_manager, history_manager, rag_engine, system_prompt=None):
        """Initialize the chat manager.
        
        Args:
            model_manager: ModelManager instance to handle LLM interactions
            history_manager: HistoryManager for storing/retrieving chat history
            rag_engine: RAGEngine for context augmentation
            system_prompt: Optional system prompt to set context
        """
        self.model_manager = model_manager
        self.history_manager = history_manager
        self.rag_engine = rag_engine
        self.current_session = []
        
        # Initialize session with system prompt if provided
        if system_prompt:
            self.current_session.append({"role": "system", "content": system_prompt})
    
    def run_chat_loop(self):
        """Run the main chat interaction loop."""
        print(f"Starting AI Desk Buddy with {self.model_manager.model_name}.")
        print("Type your message (or 'exit' to quit):")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                # Add current session to stored history before exiting
                self.history_manager.add_session(self.current_session)
                print("Shutting down AI Desk Buddy.")
                break
            
            # Process user input
            self._process_user_message(user_input)
    
    def _process_user_message(self, user_input):
        """Process a user message and generate a response."""
        # Add user input to current session
        user_message = {"role": "user", "content": user_input}
        self.current_session.append(user_message)
        
        # Get relevant context using RAG first, before adding the message to RAG engine
        augmented_messages = self.rag_engine.augment_with_context(
            self.current_session, user_input
        )
        
        # Generate and display response
        try:
            print("AI: ", end="", flush=True)
            
            # Stream response from model
            response_text = ""
            for token in self.model_manager.generate_stream(augmented_messages):
                print(token, end="", flush=True)
                response_text += token
            
            print()  # New line after response
            
            # Add assistant response to current session
            assistant_message = {"role": "assistant", "content": response_text}
            self.current_session.append(assistant_message)
            
            # Now add both messages to RAG engine after response generation
            # User message might not be added due to filtering in add_message
            self.rag_engine.add_message(user_message)
            self.rag_engine.add_message(assistant_message)
            
        except Exception as e:
            print(f"\nError: {e}")
            self._attempt_recovery()
    
    def _attempt_recovery(self):
        """Try to recover from connection errors."""
        try:
            print("Attempting to recover connection...")
            self.model_manager.test_connection()
            print("Connection recovered.")
        except:
            print("Recovery failed. The Ollama service may need to be restarted.")