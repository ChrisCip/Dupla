"""Content-addressed cache for expensive steps (rendered pages, optional APS JSON)."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ArtifactCache:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._render = self.root / "rendered"
        self._render.mkdir(exist_ok=True)
        self._aps = self.root / "aps"
        self._aps.mkdir(exist_ok=True)

    def render_key(self, pdf_path: Path) -> str:
        return _sha256_file(Path(pdf_path))

    def try_get_rendered_dir(self, pdf_path: Path) -> Path | None:
        key = self.render_key(pdf_path)
        d = self._render / key
        meta = d / "meta.json"
        if d.is_dir() and meta.is_file():
            return d / "pages"
        return None

    def publish_rendered_dir(self, pdf_path: Path, source_pages_dir: Path) -> Path:
        """Store a copy of rendered PNGs for reuse. Returns the canonical pages dir in cache."""
        key = self.render_key(pdf_path)
        d = self._render / key
        pages = d / "pages"
        if pages.is_dir():
            shutil.rmtree(pages)
        pages.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_pages_dir, pages)
        (d / "meta.json").write_text(
            json.dumps({"source_pdf": str(pdf_path.resolve())}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pages

    def materialize_render_to(
        self,
        pdf_path: Path,
        dest_pages_dir: Path,
    ) -> bool:
        """
        If cache hit, copy cached pages to dest. Returns True if used cache.
        """
        src = self.try_get_rendered_dir(pdf_path)
        if src is None:
            return False
        if dest_pages_dir.is_dir():
            shutil.rmtree(dest_pages_dir)
        dest_pages_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest_pages_dir)
        return True


def cache_aps_fingerprint(dwg_path: Path) -> str:
    return _sha256_file(dwg_path)
