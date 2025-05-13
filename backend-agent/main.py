import csv
import json
import os

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_file
from flask_cors import CORS
from flask_sock import Sock
from werkzeug.utils import secure_filename

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

# Set up the upload folder dynamically
UPLOAD_FOLDER = './uploads'  # You can change this to a different path if needed
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def send_intro(sock):
    """
    Sends the intro via the websocket connection.
    """
    with open('data/intro.txt', 'r') as f:
        intro = f.read()
        sock.send(json.dumps({'type': 'message', 'data': intro}))


@sock.route('/agent')
def query_agent(sock):
    """
    Websocket route for the frontend to send prompts to the agent and receive
    responses as well as status updates.
    """
    status.sock = sock
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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        # Optional: parse CSV immediately
        try:
            with open(path, newline='') as f:
                reader = csv.DictReader(f)
                data = list(reader)

            return jsonify({'message': 'CSV uploaded successfully', 'data': data})

        except Exception as e:
            return jsonify({'error': f'Error reading CSV: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file type'}), 400


# Endpoint to fetch all the vendors from the uploaded CSV
@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    # Check if CSV file exists
    error_response = check_csv_exists('STARS_RESULTS.csv')
    if error_response:
        print("❌ CSV not found or error from check_csv_exists")
        return error_response

    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'STARS_RESULTS.csv')
        print(f"📄 Reading CSV from: {file_path}")
        with open(file_path, mode='r') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        # Extract unique vendors
        vendors = list(set([model['vendor'] for model in data if 'vendor' in model]))
        return jsonify(vendors)

    except Exception as e:
        print(f"🔥 Exception occurred: {str(e)}")  # DEBUG PRINT
        return jsonify({'error': f'Error reading vendors from CSV: {str(e)}'}), 500


# Endpoint to fetch heatmap data from the uploaded CSV
@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'STARS_RESULTS.csv')  # Use dynamic upload folder path
    try:
        with open(file_path, mode='r') as f:
            reader = csv.DictReader(f)
            data = list(reader)

        return jsonify(data)

    except Exception as e:
        return jsonify({'error': f'Error reading heatmap data from CSV: {str(e)}'}), 500


# Endpoint to fetch heatmap data filtered by vendor from the uploaded CSV
@app.route('/api/heatmap/<name>', methods=['GET'])
def get_filtered_heatmap(name):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'STARS_RESULTS.csv')  # Use dynamic upload folder path
    try:
        with open(file_path, mode='r') as f:
            reader = csv.DictReader(f)
            data = list(reader)

        # Filter data by vendor name
        filtered_data = [model for model in data if model['vendor'].lower() == name.lower()]
        return jsonify(filtered_data)

    except Exception as e:
        return jsonify({'error': f'Error reading filtered heatmap data from CSV: {str(e)}'}), 500


# Endpoint to fetch all attacks from the uploaded CSV
@app.route('/api/attacks', methods=['GET'])
def get_attacks():
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'attacks.csv')  # Use dynamic upload folder path
    try:
        with open(file_path, mode='r') as f:
            reader = csv.DictReader(f)
            data = list(reader)

        return jsonify(data)

    except Exception as e:
        return jsonify({'error': f'Error reading attacks data from CSV: {str(e)}'}), 500


def check_csv_exists(file_name):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    if not os.path.exists(file_path):
        return jsonify({'error': f'{file_name} not found. Please upload the file first.'}), 404
    return None  # No error, file exists


if __name__ == '__main__':
    if not os.getenv('API_KEY'):
        print('No API key is set! Access is unrestricted.')
    port = os.getenv('BACKEND_PORT', 8080)
    debug = bool(os.getenv('DEBUG', False))
    app.run(host='0.0.0.0', port=int(port), debug=debug)
