import os
from importlib.metadata import version

from dotenv import load_dotenv
from flask_cors import CORS
from flask_sock import Sock

from app import create_app
from app.routes import register_routes
from status import LangchainStatusCallbackHandler

# -----------------------------
# Version & Environment Setup
# -----------------------------
__version__ = version('stars')
load_dotenv()

# -----------------------------
# Optional Agent Initialization
# -----------------------------
agent_instance = None
if not os.getenv('DISABLE_AGENT'):
    from agent import agent as agent_instance

# -----------------------------
# Flask App & WebSocket Setup
# -----------------------------
app = create_app()
sock = Sock(app)

# Configure CORS with allowed origins, if any
allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
# Clean up empty strings from allowed_origins
allowed_origins = [origin.strip() for origin in allowed_origins
                   if origin.strip()]
if allowed_origins:
    CORS(app, resources={r"/*": {"origins": allowed_origins}})
else:
    CORS(app)

# ---------------------------------------------------
# Langfuse to analyze tracings and help in debugging.
# ---------------------------------------------------
langfuse_handler = None
if os.getenv('ENABLE_LANGFUSE'):
    from langfuse.callback import CallbackHandler
    # Initialize Langfuse handler
    langfuse_handler = CallbackHandler(
        secret_key=os.getenv('LANGFUSE_SK'),
        public_key=os.getenv('LANGFUSE_PK'),
        host=os.getenv('LANGFUSE_HOST')
    )
else:
    print('Starting server without Langfuse. Set ENABLE_LANGFUSE variable to \
enable tracing with Langfuse.')

status_callback_handler = LangchainStatusCallbackHandler()
callbacks = {'callbacks': [langfuse_handler, status_callback_handler]
             } if langfuse_handler else {
                 'callbacks': [status_callback_handler]}

register_routes(app, sock, agent_instance, callbacks)

# -----------------------------
# Main Server Entry
# -----------------------------
if __name__ == '__main__':
    if not os.getenv('API_KEY'):
        print('No API key is set! Access is unrestricted.')
    port = os.getenv('BACKEND_PORT', 8080)
    debug = bool(os.getenv('DEBUG', False))
    print(f'Loading backend version {__version__} on port {port}')
    app.run(host='0.0.0.0', port=int(port), debug=debug)
