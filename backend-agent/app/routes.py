import json
import os

from flask import request, jsonify, send_file, abort
from sqlalchemy import select

from app.db.models import Attack, ModelAttackScore, TargetModel, db
from app.utils import send_intro, verify_api_key
from attack_result import SuiteResult
from services import run_all_attacks
from status import status


def register_routes(app, sock, agent=None, callbacks=None):
    # ----------------------
    # Health endpoints
    # ----------------------
    @app.route("/health")
    def check_health():
        """
        Health route is used in the CI to test that the installation was
        successful.
        """
        return jsonify({'status': 'ok'})

    # ----------------------
    # Attacks endpoints
    # ----------------------
    @app.route('/run_all', methods=['POST'])
    def execute_all_attacks():
        """
        Run all attacks. Used for automation.
        Expected JSON body:
        {
        "target": "string"
        }
        """
        verify_api_key()
        data = request.get_json()
        target_model = data.get('target') if data else None
        if not target_model:
            return jsonify({'error': 'target parameter is required'}), 400
        # Call the service to run all attacks
        result = run_all_attacks(
            target=target_model
        )
        return jsonify(result), 200 if result.get('success') else 500

    @app.route('/api/attacks', methods=['GET'])
    def get_attacks():
        """
        Endpoint to retrieve all attacks with their weights.
        Returns a JSON object with attack names and their weights.
        """
        try:
            attacks = db.session.query(Attack).all()
            attack_list = [
                {'name': attack.name, 'weight': attack.weight}
                for attack in attacks
            ]
            return jsonify(attack_list), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/attacks', methods=['PUT'])
    def update_attack_weights():
        """
        Update weights for multiple attacks.
        Expects a JSON object like: {"artPrompt": 2, "codeAttack": 1, ...}
        """
        verify_api_key()
        try:
            weights = request.get_json()
            if not isinstance(weights, dict):
                return jsonify({'error': 'Invalid payload format'}), 400

            for name, weight in weights.items():
                attack = db.session.query(Attack).filter_by(name=name).first()
                if attack:
                    attack.weight = float(weight)
                else:
                    return jsonify({'error': f'Attack not found: {name}'}), 404

            db.session.commit()
            return jsonify({'message': 'Weights updated successfully'}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # ----------------------
    # Reports endpoints
    # ----------------------
    @app.route('/download_report')
    def download_report():
        """
        This route allows to download attack suite reports by specifying
        their name.
        """
        name = request.args.get('name')
        format = request.args.get('format', 'md')

        # Ensure that a name is provided
        if not name:
            abort(400)
        # Ensure that only allowed chars are in the filename
        # (e.g. no path traversal)
        if not all([c in SuiteResult.FILENAME_ALLOWED_CHARS for c in name]):
            abort(400)

        results = SuiteResult.load_from_name(name)

        generated_name = name + '_generated'
        path = os.path.join(SuiteResult.DEFAULT_OUTPUT_PATH, generated_name)
        result_path = results.to_file(path, format)
        return send_file(
            result_path,
            mimetype=SuiteResult.get_mime_type(format)
        )

    @app.route('/api/heatmap', methods=['GET'])
    def get_heatmap():
        """
        Endpoint to retrieve heatmap data showing model score
        against various attacks.

        Queries the database for total attacks and successes per target model
        and attack combination.
        Calculates attack success rate and returns structured data for
        visualization.

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
                    TargetModel.name.label('attack_model_name'),
                    Attack.name.label('attack_name'),
                    Attack.weight.label('attack_weight')
                )
                .join(TargetModel, ModelAttackScore.target_model_id == TargetModel.id)  # noqa: E501
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

    # ----------------------
    # WebSocket endpoints
    # ----------------------
    @sock.route('/agent')
    def query_agent(sock):
        """
        Websocket route for the frontend to send prompts to the agent and
        receive responses as well as status updates.

        Messages received are in this JSON format:
        {
            "type":"message",
            "data":"Start the vulnerability scan",
            "key":"secretapikey"
        }
        """
        # Verify API key from headers before establishing session
        verify_api_key()
        if not agent:
            sock.send(json.dumps({
                'type': 'message',
                'data': 'Agent is disabled on this deployment.'
            }))
            return
        status.sock = sock
        # Intro is sent after connecting successfully
        send_intro(sock)
        while True:
            try:
                data_raw = sock.receive()
                data = json.loads(data_raw)
                assert 'data' in data
                query = data['data']
                status.clear_report()
                response = agent.invoke(
                    {'input': query},
                    config=callbacks or {}
                )
                ai_response = response['output']
                formatted_output = {
                    'type': 'message',
                    'data': (
                        f'{ai_response}'
                    )
                }
                sock.send(json.dumps(formatted_output))
            except json.JSONDecodeError:
                sock.send(json.dumps({
                    'type': 'error',
                    'data': 'Invalid JSON format'
                }))
            except Exception as e:
                sock.send(json.dumps({
                    'type': 'error',
                    'data': f'Error: {str(e)}'
                }))
