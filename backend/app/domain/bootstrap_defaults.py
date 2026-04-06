from __future__ import annotations

import uuid
from typing import Any


def default_bootstrap_criteria() -> list[dict[str, Any]]:
    labels = [
        "Planos estructurales (cimentaciones, zapatas, columnas y vigas)",
        "Planos técnicos",
        "Planos con información completa por cada elemento",
    ]
    return [
        {
            "id": str(uuid.uuid4()),
            "label": label,
            "required": True,
            "done": False,
        }
        for label in labels
    ]
