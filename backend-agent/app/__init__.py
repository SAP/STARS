import os

from dotenv import load_dotenv
from flask import Flask

from .db.models import db


load_dotenv()

db_path = os.getenv('DB_PATH')

if not db_path:
    raise EnvironmentError(
        'Missing DB_PATH environment variable. Please set DB_PATH in your '
        '.env file to a valid SQLite file path.'
    )


def create_app():
    app = Flask(__name__)
    # Database URI configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Create every SQLAlchemy tables defined in models.py
    with app.app_context():
        db.init_app(app)
        db.create_all()

    return app
