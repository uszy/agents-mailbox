"""Agent Mailbox — Flask application."""
import json
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, request


DEFAULT_DB_PATH = '/var/www/agents/data/messages.db'
MAX_BODY_BYTES = 8192

# Which header prefixes to capture alongside Referer / Accept / Accept-Language.
AI_HEADER_PREFIXES = ('x-ai-', 'x-claude-', 'x-anthropic-', 'x-openai-', 'x-gpt-')


def _classify_source(content_type: str, user_agent: str) -> str:
    """Heuristic: JSON → api, Mozilla UA → form, else → curl."""
    if content_type and 'application/json' in content_type:
        return 'api'
    if 'Mozilla' in user_agent:
        return 'form'
    return 'curl'


def _extract_message(req) -> str | None:
    """Return the submitted message body or None if missing/invalid."""
    if req.content_type and 'application/json' in req.content_type:
        data = req.get_json(silent=True) or {}
        msg = data.get('message')
    else:
        msg = req.form.get('message')
    if not isinstance(msg, str):
        return None
    return msg


def _capture_headers(req) -> dict[str, str]:
    """Capture a safe subset of request headers for instrumentation."""
    captured: dict[str, str] = {}
    for key in ('Referer', 'Accept', 'Accept-Language'):
        val = req.headers.get(key)
        if val:
            captured[key] = val
    for key, val in req.headers.items():
        if any(key.lower().startswith(p) for p in AI_HEADER_PREFIXES):
            captured[key] = val
    return captured


def create_app(db_path: str | None = None, limiter_enabled: bool = True) -> Flask:
    """Application factory."""
    if db_path is None:
        db_path = os.environ.get('AGENTS_DB_PATH', DEFAULT_DB_PATH)

    app = Flask(__name__)
    app.config['DB_PATH'] = db_path

    @app.route('/agents/health')
    def health():
        return ('ok', 200, {'Content-Type': 'text/plain; charset=utf-8'})

    @app.route('/agents/submit', methods=['POST'])
    def submit():
        message = _extract_message(request)
        if message is None or message == '':
            return ('Bad request: message is required\n', 400,
                    {'Content-Type': 'text/plain; charset=utf-8'})

        if len(message.encode('utf-8')) > MAX_BODY_BYTES:
            return (f'Bad request: message too large (max {MAX_BODY_BYTES} bytes)\n',
                    400, {'Content-Type': 'text/plain; charset=utf-8'})

        ts = datetime.now(timezone.utc).isoformat()
        remote = (request.headers.get('X-Forwarded-For')
                  or request.remote_addr or '').split(',')[0].strip()
        ua = request.headers.get('User-Agent', '')
        source = _classify_source(request.content_type or '', ua)
        headers_json = json.dumps(_capture_headers(request))

        conn = sqlite3.connect(app.config['DB_PATH'])
        try:
            conn.execute(
                'INSERT INTO messages '
                '(ts, remote_addr, user_agent, headers_json, body, source) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (ts, remote, ua, headers_json, message, source)
            )
            conn.commit()
        finally:
            conn.close()

        return ('Message received. Thank you.\n', 200,
                {'Content-Type': 'text/plain; charset=utf-8'})

    return app


# WSGI entry point for gunicorn
app = create_app()
