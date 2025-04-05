"""
ContextEngine - A RAG implementation for providing conversation context
"""
import os
import json
from typing import List, Dict, Any

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Context retrieval will be limited.")
    print("Install with: pip install sentence-transformers")

class ContextEngine:
    def __init__(self, history_service, embeddings_file="chat_embeddings.json", model_name="all-MiniLM-L6-v2"):
        self.history_service = history_service
        self.embeddings_file = embeddings_file
        self.model_name = model_name
        self.model = None
        self.embeddings = self._load_embeddings()
        self.current_user_query = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                print(f"Context: Loaded embedding model {model_name}")
                self._update_embeddings()
            except Exception as e:
                print(f"Warning: Failed to initialize embeddings model: {e}")
                self.model = None
    
    def _load_embeddings(self) -> Dict[str, Any]:
        if os.path.exists(self.embeddings_file):
            try:
                with open(self.embeddings_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load embeddings file: {e}")
        return {"messages": [], "vectors": []}
    
    def _save_embeddings(self):
        try:
            with open(self.embeddings_file, "w") as f:
                json.dump(self.embeddings, f)
        except IOError as e:
            print(f"Warning: Could not save embeddings: {e}")
    
    def _update_embeddings(self):
        if not self.model:
            return
        all_messages = self.history_service.get_all_messages()
        new_messages = []
        existing_messages = [msg["content"] for msg in self.embeddings["messages"]]
        for msg in all_messages:
            if msg["role"] != "system" and msg["content"] not in existing_messages:
                new_messages.append(msg)
        if not new_messages:
            return
        try:
            texts = [msg["content"] for msg in new_messages]
            new_vectors = self.model.encode(texts).tolist()
            for i, msg in enumerate(new_messages):
                self.embeddings["messages"].append({
                    "content": msg["content"],
                    "role": msg["role"],
                    "session_id": msg.get("session_id", "unknown"),
                    "timestamp": msg.get("timestamp", "")
                })
                self.embeddings["vectors"].append(new_vectors[i])
            self._save_embeddings()
            print(f"Context: Added {len(new_messages)} messages to embeddings")
        except Exception as e:
            print(f"Warning: Failed to generate embeddings: {e}")
    
    def _compute_similarity(self, query_vector, doc_vector) -> float:
        return sum(a * b for a, b in zip(query_vector, doc_vector))
    
    def augment_with_context(self, current_messages: List[Dict[str, str]], latest_input: str) -> List[Dict[str, str]]:
        self.current_user_query = latest_input
        if not self.model or not self.embeddings["messages"]:
            return current_messages
        try:
            query_vector = self.model.encode(latest_input).tolist()
            similarities = [(i, self._compute_similarity(query_vector, doc_vector)) 
                            for i, doc_vector in enumerate(self.embeddings["vectors"])]
            similarities.sort(key=lambda x: x[1], reverse=True)
            filtered_similarities = [(i, score) for i, score in similarities 
                                     if self.embeddings["messages"][i]["content"] != latest_input]
            top_indices = [i for i, _ in filtered_similarities[:3]]
            if not top_indices:
                return current_messages
            top_messages = [self.embeddings["messages"][i] for i in top_indices]
            print("Context: Found relevant information:")
            for msg in top_messages:
                print(f"- [{msg['role']}]: {msg['content'][:50]}...")
            context_content = "Here is some relevant context from previous conversations:\n\n"
            for msg in top_messages:
                context_content += f"[{msg['role']}]: {msg['content']}\n\n"
            augmented_messages = list(current_messages)
            insert_pos = 0
            for i, msg in enumerate(augmented_messages):
                if msg["role"] == "system":
                    insert_pos = i + 1
                else:
                    break
            augmented_messages.insert(insert_pos, {"role": "system", "content": context_content})
            return augmented_messages
        except Exception as e:
            print(f"Warning: Error in context retrieval: {e}")
            return current_messages
    
    def add_message(self, message: Dict[str, str]):
        if not self.model or message["role"] == "system" or message["content"] == self.current_user_query:
            return
        try:
            existing_contents = [msg["content"] for msg in self.embeddings["messages"]]
            if message["content"] in existing_contents:
                return
            vector = self.model.encode(message["content"]).tolist()
            self.embeddings["messages"].append({
                "content": message["content"],
                "role": message["role"],
                "session_id": message.get("session_id", "unknown"),
                "timestamp": message.get("timestamp", "")
            })
            self.embeddings["vectors"].append(vector)
            self._save_embeddings()
        except Exception as e:
            print(f"Warning: Failed to add message to embeddings: {e}")