"""Download remote DWG/PDF into a run input directory (thread-safe file IO)."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("dupla.api.download")


def download_to_file(
    url: str,
    dest: Path,
    *,
    max_bytes: int,
    timeout_seconds: float,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout_seconds) as response:
        response.raise_for_status()
        with open(dest, "wb") as handle:
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    try:
                        dest.unlink(missing_ok=True)
                    except OSError:
                        pass
                    raise ValueError(f"Download exceeds max_bytes={max_bytes}")
                handle.write(chunk)
    logger.info("Downloaded %s -> %s (%d bytes)", url, dest, total)


def _task(item: dict[str, Any]) -> tuple[str, str, Path | None, str | None]:
    key = str(item["key"])
    url = str(item["url"])
    path = item["path"]
    if not url or not str(url).strip():
        return key, url, None, "empty url"
    try:
        path = Path(path)
        download_to_file(
            url,
            path,
            max_bytes=int(item["max_bytes"]),
            timeout_seconds=float(item["timeout_seconds"]),
        )
        return key, url, path, None
    except Exception as exc:  # noqa: BLE001
        return key, url, None, str(exc)


def download_batch(
    tasks: list[dict[str, Any]],
    *,
    max_workers: int = 4,
) -> dict[str, str | None]:
    """
    tasks: { key, url, path (Path|str), max_bytes, timeout_seconds }
    Returns: { key: error message or None if ok }
    """
    out: dict[str, str | None] = {}
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        futs = {pool.submit(_task, t): t["key"] for t in tasks}
        for fut in as_completed(futs):
            key, _url, _path, err = fut.result()
            out[key] = err
    return out
