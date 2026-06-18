"""DWG path/name normalization for cross-source file matching in reports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from coordination.core.models_25d import Element25D

_DRIVE_PREFIX_RE = re.compile(r"^[a-zA-Z]:")


def normalize_dwg_identity(path_or_name: str) -> str:
    """Normalize a DWG path or filename for stable comparison."""
    raw = str(path_or_name or "").strip()
    if not raw:
        return ""
    normalized = raw.replace("\\", "/")
    if normalized.startswith("//"):
        normalized = normalized[2:]
    normalized = _DRIVE_PREFIX_RE.sub("", normalized)
    normalized = normalized.lstrip("/")
    normalized = " ".join(normalized.split())
    lowered = normalized.lower()
    if lowered.endswith(".dwg"):
        return lowered
    if lowered.endswith(".dwg/"):
        return lowered.rstrip("/")
    return lowered


def dwg_basename_key(path_or_name: str) -> str:
    """Normalized basename key for a DWG path or filename."""
    return normalize_dwg_identity(Path(str(path_or_name or "")).name)


def _alias_keys(value: str, alias_map: dict[str, str] | None) -> set[str]:
    keys = {normalize_dwg_identity(value), dwg_basename_key(value)}
    if not alias_map:
        return {k for k in keys if k}
    for full_path, alias in alias_map.items():
        alias_norm = normalize_dwg_identity(alias)
        full_norm = normalize_dwg_identity(full_path)
        full_base = dwg_basename_key(full_path)
        val_norm = normalize_dwg_identity(value)
        val_base = dwg_basename_key(value)
        if val_norm in {full_norm, full_base, alias_norm, dwg_basename_key(alias)}:
            keys.update({full_norm, full_base, alias_norm, dwg_basename_key(alias)})
        if val_base in {full_norm, full_base, alias_norm, dwg_basename_key(alias)}:
            keys.update({full_norm, full_base, alias_norm, dwg_basename_key(alias)})
    return {k for k in keys if k}


def dwg_paths_equivalent(
    left: str,
    right: str,
    *,
    alias_map: dict[str, str] | None = None,
) -> bool:
    """Return True when two DWG references refer to the same file."""
    if not left or not right:
        return False
    if left == right:
        return True
    left_keys = _alias_keys(left, alias_map)
    right_keys = _alias_keys(right, alias_map)
    if left_keys & right_keys:
        return True
    return False


def element_source_file(element: Element25D) -> str:
    """Best-effort DWG path/name for an element."""
    source_ref = str(element.source_ref or "")
    if "|" in source_ref:
        file_part = source_ref.split("|", 1)[0].strip()
        if file_part:
            return file_part
    metadata = element.metadata or {}
    for key in ("source_file", "file_name", "file_path"):
        value = metadata.get(key)
        if value:
            return str(value)
    return ""


def element_belongs_to_file(
    element: Element25D,
    file_ref: str,
    *,
    alias_map: dict[str, str] | None = None,
) -> bool:
    """True when element traces to the given DWG path or basename."""
    if not file_ref:
        return False
    source_file = element_source_file(element)
    if not source_file:
        return False
    return dwg_paths_equivalent(source_file, file_ref, alias_map=alias_map)


def lookup_semantic_by_file(
    semantic_by_file: dict[str, list[Any]],
    file_ref: str,
    *,
    alias_map: dict[str, str] | None = None,
) -> list[Any]:
    """Lookup semantic elements using tolerant DWG identity keys."""
    if not file_ref:
        return []
    for key, items in semantic_by_file.items():
        if dwg_paths_equivalent(key, file_ref, alias_map=alias_map):
            return items
    return []
