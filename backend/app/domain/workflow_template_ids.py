"""UUID deterministas alineados con la migración `019_workflow_templates`."""

from __future__ import annotations

import uuid

LEGACY_WORKFLOW_TEMPLATE_ID = uuid.uuid5(uuid.NAMESPACE_URL, "dupla:workflow_template:legacy")


def legacy_step_uuid_for_phase(phase_value: str) -> uuid.UUID:
    return uuid.uuid5(LEGACY_WORKFLOW_TEMPLATE_ID, f"step:{phase_value}")
