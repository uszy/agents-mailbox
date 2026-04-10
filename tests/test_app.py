"""Tests for the Flask mailbox app."""


def test_health_ok(client):
    """GET /agents/health returns 200 with plain-text 'ok'."""
    resp = client.get('/agents/health')
    assert resp.status_code == 200
    assert resp.data == b'ok'
    assert resp.headers['Content-Type'].startswith('text/plain')
