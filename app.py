from flask import Flask, request, jsonify, render_template, session
import uuid
import logging
from datetime import datetime
import os
import threading
import time
from src.graphs.finalAgentGraph import sparrowAgent
from langchain_core.messages import HumanMessage, AIMessage
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conversations = {}
conversations_lock = threading.Lock()


def ensure_langchain_message(message):
    """Ensure a message is a proper LangChain message object"""
    if isinstance(message, (HumanMessage, AIMessage)):
        return message
    elif isinstance(message, dict):
        content = message.get('content', str(message))
        message_type = message.get('type', 'ai')
        if message_type == 'human':
            return HumanMessage(content=content)
        else:
            return AIMessage(content=content)
    elif isinstance(message, str):
        return AIMessage(content=message)
    else:
        return AIMessage(content=str(message))


def clean_messages_list(messages):
    """Ensure all messages are valid LangChain message objects"""
    return [ensure_langchain_message(msg) for msg in messages]


@app.route('/')
def index():
    """Serve main chat interface"""
    return "<h1>Sparrow Agent API</h1><p>POST to <code>/chat</code> to talk with the agent.</p>"


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json(force=True)
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'success': False, 'error': 'Empty message'})

        thread_id = session.get('thread_id')
        if not thread_id:
            thread_id = str(uuid.uuid4())
            session['thread_id'] = thread_id

        with conversations_lock:
            if thread_id not in conversations:
                conversations[thread_id] = {
                    'messages': [],
                    'notes': [],
                    'query_brief': '',
                    'final_message': '',
                    'created_at': datetime.now(),
                    'last_updated': datetime.now()
                }
            conversation = conversations[thread_id]

        human_message = HumanMessage(content=user_message)
        conversation['messages'].append(human_message)
        conversation['last_updated'] = datetime.now()

        cleaned_messages = clean_messages_list(conversation['messages'])

        sparrow_input = {
            'messages': cleaned_messages,
            'notes': conversation.get('notes', []),
            'query_brief': conversation.get('query_brief', ''),
            'final_message': conversation.get('final_message', '')
        }

        logger.info(f"[{thread_id}] Processing message: {user_message[:100]}")

        result = sparrowAgent.invoke(sparrow_input)

        response_message = ""
        ai_message = None

        if result.get('final_message'):
            response_message = result['final_message']
            ai_message = AIMessage(content=response_message)
        else:
            result_messages = clean_messages_list(result.get('messages', []))
            last_user_index = max(
                (i for i, msg in enumerate(result_messages) if isinstance(msg, HumanMessage)),
                default=-1
            )
            for i in range(last_user_index + 1, len(result_messages)):
                msg = result_messages[i]
                if isinstance(msg, AIMessage) and msg.content.strip():
                    response_message = msg.content
                    ai_message = msg
                    break

        if not response_message:
            response_message = "I'm processing your request. Could you provide more details?"
            ai_message = AIMessage(content=response_message)

        status_info = ""
        if result.get('execution_jobs'):
            status_info = f"Executed: {', '.join(result['execution_jobs'])}"
        elif result.get('notes') and isinstance(result['notes'], list) and result['notes']:
            status_info = str(result['notes'][-1])

        with conversations_lock:
            if result.get('messages'):
                conversation['messages'] = clean_messages_list(result['messages'])
            else:
                conversation['messages'].append(ai_message)

            # Deduplicate
            seen = set()
            unique_messages = []
            for msg in conversation['messages']:
                key = (type(msg).__name__, getattr(msg, "content", str(msg)))
                if key not in seen:
                    seen.add(key)
                    unique_messages.append(msg)
            conversation['messages'] = unique_messages

            conversation['notes'] = result.get('notes', conversation['notes'])
            conversation['query_brief'] = result.get('query_brief', conversation['query_brief'])
            conversation['final_message'] = result.get('final_message', conversation['final_message'])
            conversation['last_updated'] = datetime.now()

        logger.info(f"[{thread_id}] Response generated: {response_message[:100]}")

        return jsonify({
            'success': True,
            'response': response_message,
            'status': status_info,
            'thread_id': thread_id
        })

    except Exception as e:
        logger.exception("Error in /chat")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/health')
def health():
    """Health check endpoint"""
    with conversations_lock:
        active = len(conversations)
    return jsonify({'status': 'healthy', 'active_conversations': active, 'timestamp': datetime.now().isoformat()})


def cleanup_conversations():
    """Remove old conversations older than 24 hours"""
    while True:
        time.sleep(3600)
        cutoff = datetime.now().timestamp() - 24 * 3600
        with conversations_lock:
            old = [tid for tid, conv in conversations.items() if conv['last_updated'].timestamp() < cutoff]
            for tid in old:
                del conversations[tid]
            if old:
                logger.info(f"Cleaned up {len(old)} old conversations")


if __name__ == '__main__':
    cleanup_thread = threading.Thread(target=cleanup_conversations, daemon=True)
    cleanup_thread.start()

    port = int(os.environ.get("PORT", 7860))  # ✅ HF expects 7860
    logger.info(f"Starting Sparrow Agent Flask app on port {port}")
    app.run(host="0.0.0.0", port=port)
