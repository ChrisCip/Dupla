"""Tests for DWG identity normalization."""

from __future__ import annotations

from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.reporting.dwg_identity import (
    dwg_basename_key,
    dwg_paths_equivalent,
    element_belongs_to_file,
    normalize_dwg_identity,
)


def _element(source_file: str) -> Element25D:
    return Element25D(
        id="el1",
        source_ref=f"{source_file}|MUROS|LINE|abc",
        discipline=Discipline.ARCH,
        category="LINE",
        footprint_coords_mm=[(0, 0), (100, 0), (100, 100), (0, 100)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=3000.0, measurement_uncertainty_mm=0.0),
        metadata={"source_file": source_file},
    )


def test_windows_path_matches_basename() -> None:
    full = r"C:\Users\Enrique Casanova\Dupla\repositorios\SERENA 18\PLANOS\arq.dwg"
    assert dwg_paths_equivalent(full, "arq.dwg")


def test_forward_slash_matches_backslash() -> None:
    a = r"C:\repo\PLANOS\est.dwg"
    b = "C:/repo/PLANOS/est.dwg"
    assert dwg_paths_equivalent(a, b)


def test_duplicate_spaces_do_not_break_match() -> None:
    a = "EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg"
    b = "EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO Y DETALLES CASA.dwg"
    assert dwg_paths_equivalent(a, b)


def test_case_insensitive_match() -> None:
    assert dwg_paths_equivalent("Plan_A.DWG", "plan_a.dwg")


def test_unrelated_dwgs_do_not_match() -> None:
    assert not dwg_paths_equivalent("arq.dwg", "est.dwg")


def test_alias_map_match() -> None:
    aliases = {
        r"C:\long\path\PLANOS ARQ TORTUGA C-40 NOV 2025.dwg": "ARQ_NOV",
    }
    assert dwg_paths_equivalent("ARQ_NOV", r"C:\long\path\PLANOS ARQ TORTUGA C-40 NOV 2025.dwg", alias_map=aliases)


def test_element_belongs_to_file_windows_vs_basename() -> None:
    full = r"C:\repo\Serena 18 -PLANTA PISOS 10-10-2022.dwg"
    el = _element(full)
    assert element_belongs_to_file(el, "Serena 18 -PLANTA PISOS 10-10-2022.dwg")


def test_normalize_strips_drive_and_collapses_spaces() -> None:
    key = normalize_dwg_identity(r"C:\Foo\Bar  Baz.dwg")
    assert key == "foo/bar baz.dwg"


def test_dwg_basename_key() -> None:
    assert dwg_basename_key(r"C:\x\y\Plan.dwg") == "plan.dwg"
