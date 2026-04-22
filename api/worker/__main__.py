"""Run ``python -m worker`` from the ``api`` directory (see README)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_lib = _ROOT / "lib"
if str(_lib) not in sys.path:
    sys.path.insert(0, str(_lib))

import app.bootstrap_path  # noqa: F401, E402

from redis import Redis
from rq import Queue, Worker


def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    queue_name = os.environ.get("RQ_QUEUE_NAME", "dupla_jobs")
    conn = Redis.from_url(redis_url)
    queue = Queue(queue_name, connection=conn)
    worker = Worker([queue], connection=conn)
    worker.work()


if __name__ == "__main__":
    main()
