from __future__ import annotations

from enum import Enum


class FileDiscipline(str, Enum):
    ARQUITECTURA = "arquitectura"
    ESTRUCTURA = "estructura"
    MECANICA = "mecanica"
    ELECTRICA = "electrica"
    PLOMERIA = "plomeria"


class FileIngestStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


def parse_discipline(raw: str | None) -> FileDiscipline | None:
    if raw is None or raw.strip() == "":
        return None
    v = raw.strip().lower()
    for d in FileDiscipline:
        if d.value == v:
            return d
    return None
