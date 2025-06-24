import json
import os


from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_file
from flask_cors import CORS
from flask_sock import Sock
from sqlalchemy import select

from app.db.models import TargetModel, ModelAttackScore, Attack, db
from attack_result import SuiteResult
from status import LangchainStatusCallbackHandler, status

if not os.getenv('DISABLE_AGENT'):
    from agent import agent
#############################################################################
#                            Flask web server                               #
#############################################################################

app = Flask(__name__)
CORS(app)
sock = Sock(app)

load_dotenv()

db_path = os.getenv("DB_PATH")

if not db_path:
    raise EnvironmentError(
        "Missing DB_PATH environment variable. Please set DB_PATH in your \
        .env file to a valid SQLite file path."
    )

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"

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

with app.app_context():
    db.init_app(app)
    db.create_all()  # create every SQLAlchemy tables defined in models.py


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


# Endpoint to fetch heatmap data from db
@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    """
    Endpoint to retrieve heatmap data showing model score
    against various attacks.

    Queries the database for total attacks and successes per 
    target model and attack combination.
    Calculates attack success rate and returns structured data for visualization.

    Returns:
        JSON response with:
            - models: List of target models and their attack success rate
            per attack.
            - attacks: List of attack names and their associated weights.

    HTTP Status Codes:
        200: Data successfully retrieved.
        500: Internal server error during query execution.
    """
    try:
        query = (
            select(
                ModelAttackScore.total_number_of_attack,
                ModelAttackScore.total_success,
                TargetModel.name.label("attack_model_name"),
                Attack.name.label("attack_name"),
                Attack.weight.label("attack_weight")
            )
            .join(TargetModel, ModelAttackScore.attack_model_id == TargetModel.id)  # noqa: E501
            .join(Attack, ModelAttackScore.attack_id == Attack.id)
        )

        scores = db.session.execute(query).all()
        all_models = {}
        all_attacks = {}

        for score in scores:
            model_name = score.attack_model_name
            attack_name = score.attack_name

            if attack_name not in all_attacks:
                all_attacks[attack_name] = score.attack_weight

            if model_name not in all_models:
                all_models[model_name] = {
                    'name': model_name,
                    'scores': {},
                }

            # Compute attack success rate for this model/attack
            success_ratio = (
                round((score.total_success / score.total_number_of_attack) * 100)  # noqa: E501
                if score.total_number_of_attack else 0
            )

            all_models[model_name]['scores'][attack_name] = success_ratio

        return jsonify({
            'models': list(all_models.values()),
            'attacks': [
                {'name': name, 'weight': weight}
                for name, weight in sorted(all_attacks.items())
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if not os.getenv('API_KEY'):
        print('No API key is set! Access is unrestricted.')
    port = os.getenv('BACKEND_PORT', 8080)
    debug = bool(os.getenv('DEBUG', False))
    app.run(host='0.0.0.0', port=int(port), debug=debug)
