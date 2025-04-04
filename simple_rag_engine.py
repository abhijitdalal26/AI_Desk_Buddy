"""
SimpleRAGEngine - A simplified RAG implementation with minimal dependencies
"""
import os
import json
from typing import List, Dict, Any

# Try importing sentence transformers (most reliable embeddings)
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. RAG will be limited.")
    print("Install with: pip install sentence-transformers")

class SimpleRAGEngine:
    def __init__(self, history_manager, embeddings_file="chat_embeddings.json", model_name="all-MiniLM-L6-v2"):
        """Initialize the simple RAG engine.
        
        Args:
            history_manager: HistoryManager instance for accessing chat history
            embeddings_file: File to store message embeddings
            model_name: Name of the sentence transformer model to use
        """
        self.history_manager = history_manager
        self.embeddings_file = embeddings_file
        self.model_name = model_name
        self.model = None
        self.embeddings = self._load_embeddings()
        self.current_user_query = None  # Store the current user query to exclude from retrieval
        
        # Initialize embeddings model if available
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                print(f"RAG: Loaded embedding model {model_name}")
                
                # Generate embeddings for existing history if needed
                self._update_embeddings()
            except Exception as e:
                print(f"Warning: Failed to initialize embeddings model: {e}")
                self.model = None
    
    def _load_embeddings(self) -> Dict[str, Any]:
        """Load stored embeddings from file."""
        if os.path.exists(self.embeddings_file):
            try:
                with open(self.embeddings_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load embeddings file: {e}")
        
        # Return empty embeddings structure
        return {"messages": [], "vectors": []}
    
    def _save_embeddings(self):
        """Save embeddings to file."""
        try:
            with open(self.embeddings_file, "w") as f:
                json.dump(self.embeddings, f)
        except IOError as e:
            print(f"Warning: Could not save embeddings: {e}")
    
    def _update_embeddings(self):
        """Update embeddings for all messages that don't have them yet."""
        if not self.model:
            return
        
        # Get all messages
        all_messages = self.history_manager.get_all_messages()
        
        # Find messages that need embeddings
        new_messages = []
        existing_messages = [msg["content"] for msg in self.embeddings["messages"]]
        
        for msg in all_messages:
            if msg["role"] != "system" and msg["content"] not in existing_messages:
                new_messages.append(msg)
        
        if not new_messages:
            return
        
        # Generate embeddings for new messages
        try:
            texts = [msg["content"] for msg in new_messages]
            new_vectors = self.model.encode(texts).tolist()
            
            # Add to embeddings store
            for i, msg in enumerate(new_messages):
                self.embeddings["messages"].append({
                    "content": msg["content"],
                    "role": msg["role"],
                    "session_id": msg.get("session_id", "unknown"),
                    "timestamp": msg.get("timestamp", "")
                })
                self.embeddings["vectors"].append(new_vectors[i])
            
            # Save updated embeddings
            self._save_embeddings()
            print(f"RAG: Added {len(new_messages)} messages to embeddings")
            
        except Exception as e:
            print(f"Warning: Failed to generate embeddings: {e}")
    
    def _compute_similarity(self, query_vector, doc_vector) -> float:
        """Compute cosine similarity between two vectors."""
        # Simple dot product for normalized vectors
        return sum(a * b for a, b in zip(query_vector, doc_vector))
    
    def augment_with_context(self, current_messages: List[Dict[str, str]], latest_input: str) -> List[Dict[str, str]]:
        """Augment the current messages with relevant context from history.
        
        Args:
            current_messages: Current conversation messages
            latest_input: The latest user input to find context for
            
        Returns:
            list: Messages augmented with relevant context
        """
        # Store the current user query to exclude it from future embeddings
        self.current_user_query = latest_input
        
        if not self.model or not self.embeddings["messages"]:
            return current_messages
            
        try:
            # Compute query vector
            query_vector = self.model.encode(latest_input).tolist()
            
            # Compute similarities
            similarities = [
                (i, self._compute_similarity(query_vector, doc_vector))
                for i, doc_vector in enumerate(self.embeddings["vectors"])
            ]
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Filter out exact matches to the current query
            filtered_similarities = [(i, score) for i, score in similarities 
                                   if self.embeddings["messages"][i]["content"] != latest_input]
            
            # Select top 3 most similar messages
            top_indices = [i for i, _ in filtered_similarities[:3]]
            
            if not top_indices:
                return current_messages
                
            top_messages = [self.embeddings["messages"][i] for i in top_indices]
            
            # Debug output to verify RAG is working
            print("RAG: Found relevant context:")
            for msg in top_messages:
                print(f"- [{msg['role']}]: {msg['content'][:50]}...")
            
            # Create context message
            context_content = "Here is some relevant context from previous conversations:\n\n"
            for msg in top_messages:
                role = msg["role"]
                content = msg["content"]
                context_content += f"[{role}]: {content}\n\n"
            
            # Insert the context as a system message
            augmented_messages = list(current_messages)
            
            # Find position after system messages
            insert_pos = 0
            for i, msg in enumerate(augmented_messages):
                if msg["role"] == "system":
                    insert_pos = i + 1
                else:
                    break
            
            # Insert context
            augmented_messages.insert(
                insert_pos,
                {"role": "system", "content": context_content}
            )
            
            return augmented_messages
            
        except Exception as e:
            print(f"Warning: Error in RAG retrieval: {e}")
            return current_messages
    
    def add_message(self, message: Dict[str, str]):
        """Add a new message to the index.
           Skips adding the current user query.
        """
        if not self.model or message["role"] == "system":
            return
        
        # Skip adding the current user query to embeddings
        if message["role"] == "user" and self.current_user_query == message["content"]:
            return
            
        try:
            # Check if message already exists
            existing_contents = [msg["content"] for msg in self.embeddings["messages"]]
            if message["content"] in existing_contents:
                return
                
            # Generate embedding
            vector = self.model.encode(message["content"]).tolist()
            
            # Add to embeddings store
            self.embeddings["messages"].append({
                "content": message["content"],
                "role": message["role"],
                "session_id": message.get("session_id", "unknown"),
                "timestamp": message.get("timestamp", "")
            })
            self.embeddings["vectors"].append(vector)
            
            # Save updated embeddings
            self._save_embeddings()
            
        except Exception as e:
            print(f"Warning: Failed to add message to embeddings: {e}")