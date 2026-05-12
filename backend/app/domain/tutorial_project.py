"""Proyecto y tarjeta fijos de demostración para tutoriales y referencias en el workspace.

El seed (`python -m app.seed`) crea estos registros si no existen. El frontend puede enlazar a
`TUTORIAL_PROJECT_UUID` (mantener alineado con `frontend/src/constants/tutorialProject.ts`).
"""

from __future__ import annotations

import uuid

# Distinto de GENERAL_CONVERSATION_UUID y otros IDs reservados en migraciones.
TUTORIAL_PROJECT_UUID = uuid.UUID("cafe0001-0000-4000-8000-000000000001")
TUTORIAL_TASK_CARD_UUID = uuid.UUID("cafe0002-0000-4000-8000-000000000001")
# Misma fila insertada en migración 002 (`Por hacer`).
TASK_LIST_TODO_UUID = uuid.UUID("a0000001-0000-4000-8000-000000000001")

TUTORIAL_PROJECT_NAME = "Tutorial · Workspace Dupla"
TUTORIAL_TASK_TITLE = "Tarea de ejemplo (tutorial)"
