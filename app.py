"""Agent Mailbox — Flask application."""
import os

from flask import Flask


DEFAULT_DB_PATH = '/var/www/agents/data/messages.db'


def create_app(db_path: str | None = None, limiter_enabled: bool = True) -> Flask:
    """Application factory.

    Args:
        db_path: Override the SQLite path (tests use a tempfile).
        limiter_enabled: Disable rate limiting in most tests.
    """
    if db_path is None:
        db_path = os.environ.get('AGENTS_DB_PATH', DEFAULT_DB_PATH)

    app = Flask(__name__)
    app.config['DB_PATH'] = db_path

    @app.route('/agents/health')
    def health():
        return ('ok', 200, {'Content-Type': 'text/plain; charset=utf-8'})

    return app


# WSGI entry point for gunicorn
app = create_app()
