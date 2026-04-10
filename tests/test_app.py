"""Tests for the Flask mailbox app."""
import json as _json
import sqlite3


def test_health_ok(client):
    """GET /agents/health returns 200 with plain-text 'ok'."""
    resp = client.get("/agents/health")
    assert resp.status_code == 200
    assert resp.data == b"ok"
    assert resp.headers["Content-Type"].startswith("text/plain")


def test_submit_form_happy_path(client, tmp_db):
    """POST /agents/submit with form data stores a row and returns 200."""
    resp = client.post("/agents/submit", data={"message": "hello from a test"})
    assert resp.status_code == 200
    assert b"Message received" in resp.data

    # Verify the row is actually in the DB
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute("SELECT body, source FROM messages").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "hello from a test"
    assert rows[0][1] == "curl"  # no Mozilla UA → classified as curl

def test_submit_oversized_body_rejected(client):
    """POST /agents/submit with >8KB body returns 400."""
    big = 'A' * 8193  # 1 byte over the cap
    resp = client.post('/agents/submit', data={'message': big})
    assert resp.status_code == 400
    assert b'too large' in resp.data or b'Bad request' in resp.data


def test_submit_empty_body_rejected(client):
    """POST /agents/submit with empty message returns 400."""
    resp = client.post('/agents/submit', data={'message': ''})
    assert resp.status_code == 400


def test_submit_at_exact_cap_accepted(client):
    """POST /agents/submit with exactly 8192-byte body is accepted."""
    exact = 'B' * 8192
    resp = client.post('/agents/submit', data={'message': exact})
    assert resp.status_code == 200


def test_submit_json_body(client, tmp_db):
    """POST /agents/submit with JSON body stores the message and records source=api."""
    resp = client.post(
        '/agents/submit',
        json={'message': 'hello via JSON'},
    )
    assert resp.status_code == 200

    conn = sqlite3.connect(tmp_db)
    rows = conn.execute('SELECT body, source FROM messages').fetchall()
    conn.close()
    assert rows == [('hello via JSON', 'api')]


def test_submit_json_missing_message_rejected(client):
    """JSON without a message field returns 400."""
    resp = client.post('/agents/submit', json={'not_message': 'oops'})
    assert resp.status_code == 400


def test_submit_captures_user_agent_and_headers(client, tmp_db):
    """Submission stores user-agent, captured headers, and a timestamp."""
    resp = client.post(
        '/agents/submit',
        data={'message': 'hello'},
        headers={
            'User-Agent': 'Mozilla/5.0 Testbot/1.0',
            'Referer': 'https://example.com/',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-Claude-Source': 'experimental',
            'X-Other-Header': 'should-not-be-captured',
        },
    )
    assert resp.status_code == 200

    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        'SELECT ts, user_agent, headers_json, source FROM messages'
    ).fetchone()
    conn.close()

    ts, ua, headers_json, source = row
    assert 'Testbot' in ua
    assert source == 'form'  # Mozilla UA → form

    captured = _json.loads(headers_json)
    assert captured.get('Referer') == 'https://example.com/'
    assert captured.get('Accept-Language') == 'en-US,en;q=0.9'
    assert 'X-Claude-Source' in captured
    assert captured['X-Claude-Source'] == 'experimental'
    assert 'X-Other-Header' not in captured

    # Timestamp is ISO 8601 UTC
    assert '+00:00' in ts or 'Z' in ts


def test_per_ip_rate_limit(client_with_limiter):
    """11th rapid POST from same IP returns 429."""
    for i in range(10):
        resp = client_with_limiter.post(
            '/agents/submit', data={'message': f'hi {i}'}
        )
        assert resp.status_code == 200, f'request {i} failed: {resp.status_code}'

    resp = client_with_limiter.post(
        '/agents/submit', data={'message': 'one too many'}
    )
    assert resp.status_code == 429


def test_proxy_fix_respects_x_forwarded_for(client_with_limiter, tmp_db):
    """ProxyFix extracts the real IP from X-Forwarded-For (one hop of trust)."""
    resp = client_with_limiter.post(
        '/agents/submit',
        data={'message': 'from proxy'},
        headers={'X-Forwarded-For': '203.0.113.42'},
        environ_base={'REMOTE_ADDR': '127.0.0.1'},
    )
    assert resp.status_code == 200

    conn = sqlite3.connect(tmp_db)
    row = conn.execute('SELECT remote_addr FROM messages').fetchone()
    conn.close()
    assert row[0] == '203.0.113.42'


def test_404_returns_plain_text(client):
    """Unknown routes return plain-text 404, no stack trace."""
    resp = client.get('/agents/does-not-exist')
    assert resp.status_code == 404
    assert b'Traceback' not in resp.data
    assert resp.headers['Content-Type'].startswith('text/plain')


def test_method_not_allowed_returns_plain_text(client):
    """GET on POST-only route returns plain-text 405."""
    resp = client.get('/agents/submit')
    assert resp.status_code == 405
    assert b'Traceback' not in resp.data
    assert resp.headers['Content-Type'].startswith('text/plain')
