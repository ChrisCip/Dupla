from datetime import datetime, timezone
from pathlib import Path

from knowledge.feedback_store import Correction, FeedbackStore, apply_corrections_to_rules


def _sample_correction(index: int, *, notes: str = "ajuste") -> Correction:
    return Correction(
        project_id="proj-001",
        takeoff_key=f"wall_{index}:wall_finish_plaster",
        original_bc3_code="P0501102",
        corrected_bc3_code="P0501101",
        original_quantity=100.0,
        corrected_quantity=105.0,
        original_unit="m2",
        corrected_unit="m2",
        correction_type="quantity_adjust",
        corrector_notes=notes,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def test_feedback_store_add_load_stats_and_export(tmp_path: Path) -> None:
    path = tmp_path / "corrections.jsonl"
    store = FeedbackStore(path)
    store.add(_sample_correction(1))
    store.add(_sample_correction(2, notes="cambiar codigo por partida mas exacta"))

    reloaded = FeedbackStore(path)
    assert len(reloaded.corrections) == 2

    stats = reloaded.get_accuracy_stats()
    assert stats["total_corrections"] == 2
    assert "wall_finish_plaster" in stats["accuracy_by_type"]

    exported = reloaded.export_for_fine_tuning()
    assert len(exported) == 2
    assert exported[0]["messages"][2]["role"] == "assistant"


def test_apply_corrections_to_rules_generates_suggestions(tmp_path: Path) -> None:
    store = FeedbackStore(tmp_path / "corrections.jsonl")
    for idx in range(5):
        store.add(_sample_correction(idx, notes="el sistema subestima puertas de closet"))

    suggestions = apply_corrections_to_rules(store, rules_engine=object())

    assert suggestions
    assert suggestions[0]["occurrences"] >= 4
