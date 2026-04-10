"""One-shot DB schema initializer. Idempotent."""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    remote_addr     TEXT,
    user_agent      TEXT,
    headers_json    TEXT,
    body            TEXT NOT NULL,
    source          TEXT NOT NULL,
    prompt_variant  TEXT NOT NULL DEFAULT 'v1'
);

CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts);
CREATE INDEX IF NOT EXISTS idx_messages_ua ON messages(user_agent);
"""


def init_db(db_path: str) -> None:
    """Create the messages schema in the given SQLite database file."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '/var/www/agents/data/messages.db'
    init_db(path)
    print(f'Initialized schema in {path}')
