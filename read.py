#!/usr/bin/env python3
"""Interactive reader for the agent mailbox.

Dariusz's primary read path. Opens the messages DB in read-only mode,
lists messages newest-first, and lets the user pick one to view in full.

All displayed DB fields are run through sanitize_for_terminal before
printing, so stored ANSI escape sequences cannot hijack the terminal.

Usage:
    python3 read.py                          # defaults to the prod DB path
    python3 read.py --db /path/to/other.db   # read a different DB
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

from sanitize import sanitize_for_terminal


DEFAULT_DB = '/var/www/agents/data/messages.db'


def open_readonly(path: str) -> sqlite3.Connection:
    """Open the DB strictly read-only. An attempted write raises."""
    uri = f'file:{path}?mode=ro'
    return sqlite3.connect(uri, uri=True)


def list_messages(conn: sqlite3.Connection) -> list[tuple]:
    """Return (id, ts, user_agent, body) rows newest first."""
    return conn.execute(
        'SELECT id, ts, user_agent, body '
        'FROM messages '
        'ORDER BY ts DESC'
    ).fetchall()


def get_message(conn: sqlite3.Connection, msg_id: int) -> tuple | None:
    """Return the full row for a single message, or None."""
    return conn.execute(
        'SELECT id, ts, remote_addr, user_agent, headers_json, body, '
        'source, prompt_variant '
        'FROM messages WHERE id = ?',
        (msg_id,)
    ).fetchone()


def _to_str(v: object) -> str:
    """Coerce a DB value to str. Bytes are decoded via latin-1 (1-to-1)."""
    if isinstance(v, bytes):
        return v.decode('latin-1')
    return str(v) if v is not None else ''


def _truncate(s: str, width: int) -> str:
    if len(s) <= width:
        return s
    return s[: width - 1] + '…'


def _preview(body: str, width: int) -> str:
    flat = body.replace('\n', ' ').replace('\t', ' ')
    return _truncate(flat, width)


def print_list(rows: list[tuple]) -> dict[int, int]:
    """Print the numbered list view. Returns {row_number: message_id}."""
    if not rows:
        print('\n(empty — no messages yet)\n')
        return {}

    print(f'\n=== Agent Mailbox — {len(rows)} messages ===\n')
    print(f'  # | Date (UTC)        | Agent                                    | Preview')
    print(f'----+-------------------+------------------------------------------+-------------------------')

    mapping: dict[int, int] = {}
    for i, (msg_id, ts, ua, body) in enumerate(rows, start=1):
        ts_short = sanitize_for_terminal(_to_str(ts))[:16]
        ts_short = ts_short.replace('T', ' ')
        ua_short = _truncate(sanitize_for_terminal(_to_str(ua)), 40)
        body_short = _preview(sanitize_for_terminal(_to_str(body)), 25)
        print(f'  {i:>1} | {ts_short:<17} | {ua_short:<40} | {body_short}')
        mapping[i] = msg_id
    print()
    return mapping


def print_detail(row: tuple) -> None:
    (msg_id, ts, remote, ua, headers_json, body, source, variant) = row
    print('\n--- Message #{} -----------------------------------------------------------'.format(msg_id))
    print(f'Time:    {sanitize_for_terminal(_to_str(ts))}')
    print(f'Remote:  {sanitize_for_terminal(_to_str(remote))}')
    print(f'Source:  {sanitize_for_terminal(_to_str(source))}')
    print(f'Variant: {sanitize_for_terminal(_to_str(variant))}')
    print('User-Agent:')
    print('  ' + sanitize_for_terminal(_to_str(ua)))

    try:
        hj = _to_str(headers_json) if headers_json else ''
        headers = json.loads(hj) if hj else {}
    except (json.JSONDecodeError, TypeError):
        headers = {}
    if headers:
        print('Headers:')
        for k, v in headers.items():
            k_clean = sanitize_for_terminal(str(k))
            v_clean = sanitize_for_terminal(str(v))
            print(f'  {k_clean}: {v_clean}')

    body_str = _to_str(body)
    print('Message:')
    for line in body_str.splitlines() or ['']:
        print('  ' + sanitize_for_terminal(line))
    print('--------------------------------------------------------------------------\n')


def main() -> int:
    parser = argparse.ArgumentParser(description='Read the agent mailbox.')
    parser.add_argument('--db', default=DEFAULT_DB, help='Path to messages.db')
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f'error: database file not found: {args.db}', file=sys.stderr)
        return 1

    try:
        conn = open_readonly(str(db_path))
    except sqlite3.Error as e:
        print(f'error: could not open database: {e}', file=sys.stderr)
        return 1

    try:
        rows = list_messages(conn)
        mapping = print_list(rows)

        if not mapping:
            return 0

        while True:
            try:
                choice = input('Enter # to read (q to quit): ').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0

            if not choice or choice.lower() in ('q', 'quit', 'exit'):
                return 0

            try:
                n = int(choice)
            except ValueError:
                print('(not a number)')
                continue

            if n not in mapping:
                print(f'(no message #{n})')
                continue

            row = get_message(conn, mapping[n])
            if row is None:
                print(f'(message #{n} not found)')
                continue

            print_detail(row)
    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
