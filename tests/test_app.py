"""Tests for the Flask mailbox app."""
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
