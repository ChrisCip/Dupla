"""Tests for incident normalization and fallback chains."""

from __future__ import annotations

from coordination.reporting.incident_normalizer import (
    merge_enriched_cards,
    normalize_incident_for_reports,
    normalize_incidents_for_run,
    parse_revision_md_incidents,
)


def test_normalize_layers_from_enriched_layer_pair():
    raw = {"incident_id": "incident_0001", "file_pair": ["a.dwg", "b.dwg"]}
    enriched = {"layer_pair": "SOLAR / SOLAR", "disciplines": ["ARQUITECTURA", "ESTRUCTURA"]}
    norm = normalize_incident_for_reports(
        raw=raw,
        human_code="T-A1",
        group_code="T-A",
        enriched=enriched,
    )
    assert norm.layer_a == "SOLAR"
    assert norm.layer_b == "SOLAR"
    assert norm.provenance.layers_source == "coordination_context.layer_pair"


def test_normalize_layers_from_raw_layers():
    raw = {
        "incident_id": "incident_0002",
        "file_pair": ["a.dwg", "b.dwg"],
        "representative_conflict": {"raw_layers": ["PLAFON", "SOLAR"], "source_refs": ["a|0|L|1", "b|0|L|2"]},
    }
    norm = normalize_incident_for_reports(
        raw=raw,
        human_code="T-B1",
        group_code="T-B",
    )
    assert norm.layer_a == "PLAFON"
    assert norm.layer_b == "SOLAR"
    assert norm.provenance.layers_source == "representative_conflict.raw_layers"


def test_normalize_center_bounds_zoom_from_context_short_strings():
    raw = {"incident_id": "incident_0021", "file_pair": ["a.dwg", "b.dwg"]}
    enriched = {
        "location_short": "NPT_P1; (168,817,815, 624,648,464) mm",
        "bounds_short": "168,816,581, 624,646,757, 168,819,049, 624,650,171",
        "layer_pair": "MARCO / EST_PROYECCION",
    }
    norm = normalize_incident_for_reports(
        raw=raw,
        human_code="S-A1",
        group_code="S-A",
        enriched=enriched,
    )
    assert norm.center_x == 168817815.0
    assert norm.center_y == 624648464.0
    assert norm.provenance.center_source == "coordination_context.location_short"
    assert norm.bounds is not None
    assert norm.provenance.bounds_source == "coordination_context.bounds_short"
    assert norm.zoom_command is not None
    assert norm.zoom_command.startswith("Z W")


def test_normalize_expanded_bounds_from_center_only():
    raw = {
        "incident_id": "incident_0003",
        "file_pair": ["a.dwg", "b.dwg"],
        "plan_centroid_mm": [48000.0, 35000.0],
    }
    norm = normalize_incident_for_reports(
        raw=raw,
        human_code="T-C1",
        group_code="T-C",
    )
    assert norm.bounds is not None
    assert norm.provenance.bounds_source == "expanded_center_window"
    assert norm.zoom_command is not None
    assert norm.zoom_command.startswith("Z W")


def test_normalize_incidents_for_run_assigns_group_codes():
    primary = {
        "incidents": [
            {
                "incident_id": "incident_0001",
                "file_pair": ["arq.dwg", "est.dwg"],
                "representative_conflict": {
                    "raw_layers": ["SOLAR", "SOLAR"],
                    "plan_intersection_area_mm2": 5000,
                },
            }
        ]
    }
    context = {
        "all_incidents": [
            {
                "incident_id": "incident_0001",
                "layer_pair": "SOLAR / SOLAR",
                "location_short": "NPT_P1; (48,765, 35,327) mm",
                "severity": "high",
            }
        ]
    }
    rows = normalize_incidents_for_run(
        project_name="TORTUGA C40",
        primary_payload=primary,
        report_context=context,
    )
    assert len(rows) == 1
    assert rows[0].human_code.startswith("T-")
    assert rows[0].human_code.endswith("1")
    assert rows[0].layer_a == "SOLAR"
    assert rows[0].center_text != "no disponible"


def test_merge_enriched_cards_combines_sections():
    context = {
        "all_incidents": [{"incident_id": "a", "layer_pair": "X / Y"}],
        "defendable_incidents": [{"incident_id": "b", "layer_pair": "P / Q"}],
    }
    merged = merge_enriched_cards(context)
    assert merged["a"]["layer_pair"] == "X / Y"
    assert merged["b"]["layer_pair"] == "P / Q"


def test_parse_revision_md_incidents():
    md = """
### T-A1 — `incident_0001`

| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Centro del clash** | X: 48,765 mm · Y: 35,327 mm |

```
Z W -3441,9684 103882,64404 145019,160819
```
"""
    parsed = parse_revision_md_incidents(md)
    assert "incident_0001" in parsed
    assert parsed["incident_0001"]["layer_a"] == "SOLAR"
    assert parsed["incident_0001"]["zoom_command"].startswith("Z W")
