# llm_server.py
from flask import Flask, request, jsonify
from chat_controller import ChatController
from ollama_service import OllamaService
from history_service import HistoryService
from context_engine import ContextEngine
from task_service import TaskService
from voice_service_factory import VoiceServiceFactory

# --- Initialize your AI Desk Buddy pipeline ---
model_name     = "llama3.2:3b"
history_file   = "chat_history.json"
embeddings_file= "chat_embeddings.json"
tasks_file     = "tasks.json"
system_prompt  = """
You are AI Desk Buddy, a helpful assistant.
Use context from previous conversations to provide relevant answers.
"""

# Voice disabled for server
history_svc    = HistoryService(history_file)
ollama_svc     = OllamaService(model_name)
context_eng    = ContextEngine(history_svc, embeddings_file)
task_svc       = TaskService(tasks_file)
chat_ctrl      = ChatController(
    ollama_svc,
    history_svc,
    context_eng,
    task_svc,
    voice_service=None,
    system_prompt=system_prompt
)

# --- Flask app ---
app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    # Run through your chat controller (synchronously)
    # We'll call the internal method to get a response string
    response = chat_ctrl.ollama_service.generate(
        chat_ctrl.context_engine.augment_with_context(
            chat_ctrl.current_session + [{"role":"user","content":question}],
            question
        )
    )

    # Append to history & context
    chat_ctrl.current_session.append({"role":"user","content":question})
    chat_ctrl.current_session.append({"role":"assistant","content":response})
    chat_ctrl.history_service.add_session(chat_ctrl.current_session)
    chat_ctrl.context_engine.add_message({"role":"user","content":question})
    chat_ctrl.context_engine.add_message({"role":"assistant","content":response})

    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
