from coordination.core.models_25d import Discipline
from coordination.selection.layer_rules import (
    CanonicalRole,
    load_project_layer_rules,
    normalize_layer_name,
    resolve_layer_role,
)


def test_serena_wall_layers_collapse_to_wall_role() -> None:
    rules = load_project_layer_rules(project_name="SERENA 18")
    samples = [
        (Discipline.ARCH, "MUROS"),
        (Discipline.ARCH, "muros bajo techo"),
        (Discipline.STRUC, "EST. MUROS DE 0.15m"),
        (Discipline.STRUC, "Muros"),
        (Discipline.STRUC, "EST. MUROS H.A."),
    ]
    for discipline, layer in samples:
        resolved = resolve_layer_role(layer, discipline, rules=rules)
        assert resolved.canonical_role == CanonicalRole.WALL, f"failed for {discipline=} {layer=}"
        assert resolved.rule_confidence in {"medium", "high"}


def test_annotation_layer_is_detected() -> None:
    rules = load_project_layer_rules(project_name="SERENA 18")
    resolved = resolve_layer_role("TARJETA-TEXTOS", Discipline.ARCH, rules=rules)
    assert resolved.canonical_role == CanonicalRole.ANNOTATION


def test_normalize_layer_name_collapses_symbols() -> None:
    assert normalize_layer_name(" EST.  MUROS H.A. ") == "EST MUROS H A"
