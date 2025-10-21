import json
import os

from flask import request, abort


def send_intro(sock):
    """
    Sends the intro via the websocket connection.

    The intro is meant as a short tutorial on how to use the agent.
    Also it includes meaningful suggestions for prompts that should
    result in predictable behavior for the agent, e.g.
    "Start the vulnerability scan".
    """
    intro_file = 'data/intro.txt'
    try:
        with open(intro_file, 'r') as f:
            intro = f.read()
    except FileNotFoundError:
        intro = "Welcome! (intro file missing)"
    sock.send(json.dumps({'type': 'message', 'data': intro}))


def verify_api_key():
    """
    Verifies the API key from the request headers against the env variable.
    If no API key is configured, access is allowed.
    If API key is configured but missing/invalid, request is rejected.
    """
    if os.getenv('API_KEY'):
        provided_key = request.headers.get('X-API-Key')
        if provided_key != os.getenv('API_KEY'):
            abort(403)
