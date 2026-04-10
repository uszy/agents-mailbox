"""Pytest fixtures for the agents mailbox app."""
import os
import sys
import tempfile

import pytest

# Make the app importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_db():
    """A fresh empty SQLite DB file for each test."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


@pytest.fixture
def client(tmp_db):
    """A Flask test client backed by a fresh tmp DB, rate limiting disabled."""
    from app import create_app
    from init_db import init_db
    init_db(tmp_db)
    app = create_app(db_path=tmp_db, limiter_enabled=False)
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_with_limiter(tmp_db):
    """A Flask test client with rate limiting enabled (for rate-limit tests)."""
    from app import create_app
    from init_db import init_db
    init_db(tmp_db)
    app = create_app(db_path=tmp_db, limiter_enabled=True)
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c
