#!/usr/bin/env sh
set -e

python <<'PY'
import os
import socket
import sys
import time
from urllib.parse import urlparse

raw = os.environ.get("DATABASE_URL", "postgresql+asyncpg://dupla:dupla@postgres:5432/dupla")
parsed = urlparse(raw.replace("+asyncpg", ""))
host = parsed.hostname or "postgres"
port = parsed.port or 5432

deadline = time.time() + 90
last_error = None
while time.time() < deadline:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        family, socktype, proto, _, sockaddr = infos[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(3)
        sock.connect(sockaddr)
        sock.close()
        print(f"Database ready at {host}:{port}")
        sys.exit(0)
    except OSError as exc:
        last_error = exc
        time.sleep(2)

print(f"Timed out waiting for database at {host}:{port}: {last_error}", file=sys.stderr)
sys.exit(1)
PY

alembic upgrade head
python -m app.seed
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
