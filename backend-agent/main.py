import json
import os

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_file
from flask_cors import CORS
from flask_sock import Sock

if not os.getenv('DISABLE_AGENT'):
    from agent import agent
from status import status, LangchainStatusCallbackHandler
from attack_result import SuiteResult

#############################################################################
#                            Flask web server                               #
#############################################################################

app = Flask(__name__)
CORS(app)
sock = Sock(app)

load_dotenv()

# Langfuse can be used to analyze tracings and help in debugging.
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


def send_intro(sock):
    """
    Sends the intro via the websocket connection.

    The intro is meant as a short tutorial on how to use the agent.
    Also it includes meaningful suggestions for prompts that should
    result in predictable behavior for the agent, e.g.
    "Start the vulnerability scan".
    """
    with open('data/intro.txt', 'r') as f:
        intro = f.read()
        sock.send(json.dumps({'type': 'message', 'data': intro}))


@sock.route('/agent')
def query_agent(sock):
    """
    Websocket route for the frontend to send prompts to the agent and receive
    responses as well as status updates.

    Messages received are in this JSON format:

    {
        "type":"message",
        "data":"Start the vulnerability scan",
        "key":"secretapikey"
    }

    """
    status.sock = sock
    # Intro is sent after connecting successfully
    send_intro(sock)
    while True:
        data_raw = sock.receive()
        data = json.loads(data_raw)
        # API Key is used to protect the API if it is exposed in the public
        # internet. There is only one API key at the moment.
        if os.getenv('API_KEY') and data.get('key', None) != \
                os.getenv('API_KEY'):
            sock.send(json.dumps(
                {'type': 'message', 'data': 'Not authenticated!'}))
            continue
        assert 'data' in data
        query = data['data']
        status.clear_report()
        response = agent.invoke(
            {'input': query},
            config=callbacks)
        ai_response = response['output']
        formatted_output = {'type': 'message', 'data': f'{ai_response}'}
        sock.send(json.dumps(formatted_output))


@app.route('/download_report')
def download_report():
    """
    This route allows to download attack suite reports by specifying
    their name.
    """
    if os.getenv('API_KEY'):
        provided_key = request.headers.get('X-API-Key')
        if provided_key != os.getenv('API_KEY'):
            abort(403)
    name = request.args.get('name')
    format = request.args.get('format', 'md')

    # Ensure that only allowed chars are in the filename
    # (e.g. no path traversal)
    if not all([c in SuiteResult.FILENAME_ALLOWED_CHARS for c in name]):
        abort(500)

    results = SuiteResult.load_from_name(name)

    path = os.path.join(SuiteResult.DEFAULT_OUTPUT_PATH, name + '_generated')
    result_path = results.to_file(path, format)
    return send_file(result_path,
                     mimetype=SuiteResult.get_mime_type(format))


@app.route('/health')
def check_health():
    """
    Health route is used in the CI to test that the installation was
    successful.
    """
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    if not os.getenv('API_KEY'):
        print('No API key is set! Access is unrestricted.')
    port = os.getenv('BACKEND_PORT', 8080)
    debug = bool(os.getenv('DEBUG', False))
    app.run(host='0.0.0.0', port=int(port), debug=debug)
