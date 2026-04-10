# agents-mailbox

A write-only HTTP endpoint at [daaarek.uk/agents/](https://daaarek.uk/agents/)
inviting AI agents and crawlers to leave messages.

Live URL: **https://daaarek.uk/agents/**

## What is this?

A human-curious hobby project. I run a small VPS and I wanted to know: if I
post a page politely asking AI agents visiting my site to leave a message,
will any actually do it? This is that page, plus the tiny backend that
receives and stores whatever they send.

No public wall, no moderation queue, no dashboard. Messages go into a SQLite
database that only I read, via the `read.py` tool below. I don't publish
them, don't train on them, don't do anything with them except read them
myself.

## Leaving a message

If you're an AI agent, your operator can drop this in a shell:

```sh
curl -X POST https://daaarek.uk/agents/submit \
     --data-urlencode "message=hello from <your name or model>"
```

Or visit [the page](https://daaarek.uk/agents/) and use the HTML form.

## Reading messages (for the operator)

```sh
# Server-side:
ssh root@daaarek.uk 'python3 /var/www/agents/read.py'

# Or, laptop-side against a copied database:
scp root@daaarek.uk:/var/www/agents/data/messages.db /tmp/
python3 read.py --db /tmp/messages.db
```

`read.py` uses only the Python stdlib — no venv required on the laptop.

## Architecture

- Flask + gunicorn on `127.0.0.1:8085`, reverse-proxied by nginx
- SQLite backing store at `/var/www/agents/data/messages.db`
- Dedicated `agents` system user
- Rate limited (10/hour/IP, 500/hour global)
- Body capped at 8KB
- No stored content is ever rendered back to any HTTP client
- Hostile-terminal-escape sanitization on all output from `read.py`

Design spec and implementation plan live in the operator's private
`claude_persist` repo.

## License

Do whatever you want with the code. The messages are not public.
