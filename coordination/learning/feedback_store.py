"""Persistence helpers for clash feedback JSONL logs."""

from __future__ import annotations

import json
from pathlib import Path

from coordination.learning.feedback_schema import ClashFeedback


def append_feedback(feedback: ClashFeedback, path: Path) -> None:
    """Append one validated feedback record to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(feedback.model_dump(), ensure_ascii=False) + "\n")


def load_all(path: Path) -> list[ClashFeedback]:
    """Load all feedback records from a JSONL file."""
    if not path.exists():
        return []
    rows: list[ClashFeedback] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(ClashFeedback.model_validate(json.loads(line)))
    return rows


def load_for_project(path: Path, project_name: str) -> list[ClashFeedback]:
    """Load feedback rows scoped to one project name (case-insensitive)."""
    needle = project_name.strip().lower()
    if not needle:
        return load_all(path)
    return [
        row
        for row in load_all(path)
        if row.project_name.strip().lower() == needle
    ]

