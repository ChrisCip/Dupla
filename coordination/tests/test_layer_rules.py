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


def test_tortuga_elec_tuberia_is_route_not_slab() -> None:
    rules = load_project_layer_rules(project_name="TORTUGA C40")
    resolved = resolve_layer_role("E Tuberia Emp Losa", Discipline.MEP_ELEC, rules=rules)
    assert resolved.canonical_role == CanonicalRole.ELECTRICAL_ROUTE
    assert resolved.canonical_role != CanonicalRole.SLAB


def test_tortuga_mobiliarios_is_furniture_suppressed() -> None:
    from coordination.selection.layer_rules import is_suppressed_role

    rules = load_project_layer_rules(project_name="TORTUGA C40")
    resolved = resolve_layer_role("MOBILIARIOS", Discipline.MEP_ELEC, rules=rules)
    assert resolved.canonical_role == CanonicalRole.FURNITURE
    assert is_suppressed_role(resolved.canonical_role, confidence=resolved.rule_confidence)


# ── F-01 discipline_pair_constraints tests ────────────────────────────────────

def _tortuga_role_matrix():
    from coordination.selection.layer_rules import load_role_matrix
    role_matrix, suppress_roles, discipline_pair_constraints = load_role_matrix(project_name="TORTUGA C40")
    return role_matrix, suppress_roles, discipline_pair_constraints


def test_slab_slab_allowed_for_arq_est() -> None:
    from coordination.selection.layer_rules import role_pair_allowed
    role_matrix, _, dpc = _tortuga_role_matrix()
    assert role_pair_allowed(
        "SLAB", "SLAB",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=dpc,
        discipline_a="ARQUITECTURA",
        discipline_b="ESTRUCTURA",
    )


def test_slab_slab_blocked_for_arq_elec() -> None:
    from coordination.selection.layer_rules import role_pair_allowed
    role_matrix, _, dpc = _tortuga_role_matrix()
    assert not role_pair_allowed(
        "SLAB", "SLAB",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=dpc,
        discipline_a="ARQUITECTURA",
        discipline_b="ELECTRICIDAD",
    )


def test_slab_slab_blocked_symmetry_elec_arq() -> None:
    from coordination.selection.layer_rules import role_pair_allowed
    role_matrix, _, dpc = _tortuga_role_matrix()
    assert not role_pair_allowed(
        "SLAB", "SLAB",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=dpc,
        discipline_a="ELECTRICIDAD",
        discipline_b="ARQUITECTURA",
    )


def test_wall_electrical_route_allowed_for_arq_elec() -> None:
    from coordination.selection.layer_rules import role_pair_allowed
    role_matrix, _, dpc = _tortuga_role_matrix()
    assert role_pair_allowed(
        "WALL", "ELECTRICAL_ROUTE",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=dpc,
        discipline_a="ARQUITECTURA",
        discipline_b="ELECTRICIDAD",
    )


def test_slab_lighting_fixture_allowed_for_arq_elec() -> None:
    from coordination.selection.layer_rules import role_pair_allowed
    role_matrix, _, dpc = _tortuga_role_matrix()
    assert role_pair_allowed(
        "SLAB", "LIGHTING_FIXTURE",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=dpc,
        discipline_a="ARQUITECTURA",
        discipline_b="ELECTRICIDAD",
    )


def test_role_pair_no_discipline_pairs_is_backward_compatible() -> None:
    """Rules without discipline_pairs in YAML still allow any discipline combination."""
    from coordination.selection.layer_rules import role_pair_allowed
    role_matrix = {("WALL", "WALL"): True}
    dpc: dict = {}
    assert role_pair_allowed(
        "WALL", "WALL",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=dpc,
        discipline_a="ARQUITECTURA",
        discipline_b="ESTRUCTURA",
    )
    assert role_pair_allowed(
        "WALL", "WALL",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=None,
        discipline_a=None,
        discipline_b=None,
    )


def test_slab_slab_smoke_suppressed_arq_elec() -> None:
    """Smoke-style: a PLAFON(SLAB) vs SOLAR(SLAB) conflict in ARQ↔ELEC must be suppressed."""
    from coordination.selection.layer_rules import role_pair_allowed
    role_matrix, _, dpc = _tortuga_role_matrix()
    # ARQ:PLAFON → SLAB, ELEC:SOLAR → SLAB — the Smoke 02B false-positive pattern
    result = role_pair_allowed(
        "SLAB", "SLAB",
        role_matrix=role_matrix,
        allow_same_role=True,
        discipline_pair_constraints=dpc,
        discipline_a="ARQUITECTURA",
        discipline_b="ELECTRICIDAD",
    )
    assert not result, "SLAB↔SLAB must be suppressed for ARQ↔ELEC (F-01)"
