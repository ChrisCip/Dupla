"""
Generates a per-project REVISION_CLASHES_ARQUITECTO_{PROJECT}.md report.

The report follows the format of REVISION_CLASHES_ARQUITECTO.md:
- AutoCAD instructions for each clash
- Incidents grouped by layer pair
- Per-incident cards with ZOOM commands
- Validation bitácora table
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Helpers ────────────────────────────────────────────────────────────────────

def _project_slug(project_name: str) -> str:
    """'SERENA 18 — registro...' → 'SERENA_18'"""
    base = project_name.split("—")[0].split("–")[0].strip()
    return re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_").upper()


def _project_letter(slug: str) -> str:
    """'SERENA_18' → 'S', 'TORTUGA_C40' → 'T', 'NASAS_09' → 'N'"""
    parts = slug.split("_")
    return parts[0][0] if parts else "X"


def _area_m2(area_mm2: float) -> float:
    return round(area_mm2 / 1_000_000, 2)


def _zoom_command(bounds_mm: list[float], margin_factor: float = 0.25, min_margin_mm: float = 5_000) -> str:
    """Return AutoCAD Z W command string from plan_bounds_mm [x1,y1,x2,y2]."""
    x1, y1, x2, y2 = bounds_mm
    w = max(x2 - x1, 1)
    h = max(y2 - y1, 1)
    mx = max(w * margin_factor, min_margin_mm)
    my = max(h * margin_factor, min_margin_mm)
    return (
        f"Z W {round(x1 - mx)},{round(y1 - my)} {round(x2 + mx)},{round(y2 + my)}"
    )


def _layers_from_incident(incident: dict) -> tuple[str, str]:
    """Extract (layer_a, layer_b) from representative_conflict.source_refs."""
    rep = incident.get("representative_conflict") or {}
    refs = rep.get("source_refs") or []
    layers = []
    for ref in refs[:2]:
        parts = ref.split("|")
        layers.append(parts[1] if len(parts) > 1 else "?")
    while len(layers) < 2:
        layers.append("?")
    return layers[0], layers[1]


def _files_from_incident(incident: dict) -> tuple[str, str]:
    pair = incident.get("file_pair") or []
    a = Path(pair[0]).name if len(pair) > 0 else "?"
    b = Path(pair[1]).name if len(pair) > 1 else "?"
    return a, b


def _confidence_es(confidence: str) -> str:
    mapping = {"high": "Alta", "medium": "Media", "low": "Baja"}
    return mapping.get((confidence or "").lower(), confidence.capitalize() if confidence else "—")


def _severity_from_area(area_mm2: float) -> str:
    m2 = area_mm2 / 1_000_000
    if m2 >= 10:
        return "Alta"
    if m2 >= 1:
        return "Media"
    return "Baja"


# ── Static instructions block ───────────────────────────────────────────────────

_INSTRUCTIONS = """---

> **Cómo usar este documento**
> Este reporte es tu bitácora de trabajo. El programa detectó posibles conflictos entre planos de arquitectura y estructura. Tu labor es abrir los DWGs, ir a cada coordenada indicada, mirar con tus propios ojos y decidir: ¿es un clash real o es ruido? Al final de cada sección hay una tabla de validación donde vas marcando.

---

## INSTRUCCIONES GENERALES

### Paso 1 — Abrir los dos archivos en AutoCAD

1. Abre AutoCAD.
2. Abre el **Plano A** (Arquitectura) desde `Archivo → Abrir`.
3. Abre el **Plano B** (Estructura) en la misma sesión: `Archivo → Abrir` nuevamente.
4. Para ver ambos superpuestos: activa **"Ventanas en mosaico"** (`Ctrl + Alt + T`) o usa `Vista → Ventanas → Mosaico vertical`.
5. Alternativa: usa **DWG Compare** (`dwgcompare` en la línea de comandos) si tienes AutoCAD 2019+.

### Paso 2 — Usar el comando ZOOM para ir a las coordenadas

Cada clash tiene un comando AutoCAD listo. Cópialo y pégalo en la **Línea de Comandos**:
```
Z W X_MIN,Y_MIN X_MAX,Y_MAX
```
Ejemplo: `Z W 148000,-163000 158000,-154000`

> **Nota:** Todos los valores están en **milímetros**. Si tu DWG está en metros, divide entre 1,000.

### Paso 3 — Controlar las capas

1. Escribe `LA` para abrir el Administrador de Capas.
2. Apaga todas las capas (`Ctrl + A` → apaga ojo).
3. Prende solo las dos capas del clash que estás revisando.
4. Verifica si las geometrías se solapan.
5. Al terminar: `LA` → `Ctrl + A` → enciende todas.

### Paso 4 — Decisión final

| Decisión | Significado |
|---|---|
| ✅ **CLASH REAL** | Conflicto real de coordinación que hay que resolver. |
| ❌ **FALSO POSITIVO** | Ruido gráfico (marcos de hoja, cotas, anotaciones). |
| ⚠️ **PENDIENTE** | Necesitas más información antes de decidir. |

---
"""


# ── Incident card renderer ──────────────────────────────────────────────────────

def _incident_card(
    incident: dict,
    code: str,
    group_label: str,
) -> str:
    inc_id = incident.get("incident_id", "?")
    layer_a, layer_b = _layers_from_incident(incident)
    file_a, file_b = _files_from_incident(incident)
    area_mm2 = (incident.get("representative_conflict") or {}).get(
        "plan_intersection_area_mm2", 0
    ) or 0
    area = _area_m2(area_mm2)
    centroid = incident.get("plan_centroid_mm") or []
    bounds = incident.get("plan_bounds_mm") or []
    confidence = incident.get("confidence", "")
    level = incident.get("level_id", "—")
    members = incident.get("member_count", 1)

    cx_str = f"{round(centroid[0]):,}" if centroid else "—"
    cy_str = f"{round(centroid[1]):,}" if centroid else "—"
    severity = _severity_from_area(area_mm2)
    zoom_cmd = _zoom_command(bounds) if len(bounds) == 4 else "Z E"

    lines = [
        f"",
        f"### {code} — `{inc_id}`",
        f"",
        f"| Campo | Valor |",
        f"|---|---|",
        f"| **ID Programa** | `{inc_id}` |",
        f"| **Par** | `{file_a}` vs `{file_b}` |",
        f"| **Capas** | `{layer_a}` (ARQ) vs `{layer_b}` (EST) |",
        f"| **Área de solapamiento** | {area} m² |",
        f"| **Elementos involucrados** | {members} |",
        f"| **Severidad** | {severity} |",
        f"| **Confianza del programa** | {_confidence_es(confidence)} |",
        f"| **Nivel** | {level} |",
        f"| **Centro del clash** | X: {cx_str} mm · Y: {cy_str} mm |",
        f"",
        f"**Cómo llegar — Comando AutoCAD:**",
        f"```",
        f"{zoom_cmd}",
        f"```",
        f"",
        f"**Qué buscar:** Activa solo las capas `{layer_a}` y `{layer_b}`. "
        f"¿Se solapan los elementos de ambos planos en ese punto? "
        f"Verifica si la geometría es constructiva (muros, losas, vigas) "
        f"o anotación (marcos, títulos, símbolos).",
        f"",
        f"---",
    ]
    return "\n".join(lines)


# ── Main render function ────────────────────────────────────────────────────────

def render_revision_report(
    *,
    project_name: str,
    primary_payload: dict,
    scheduled_pairs: list[dict] | None = None,
    pair_rollups: list[dict] | None = None,
    nasas_root: Path | None = None,
    generated_at: str | None = None,
) -> str:
    """
    Render a REVISION_CLASHES_ARQUITECTO_{PROJECT}.md report.

    Args:
        project_name: Full project name from the registry.
        primary_payload: Dict as stored in primary_incidents.json.
        scheduled_pairs: List of scheduled pair dicts from pair_schedule.json.
        pair_rollups: List from coordination_report_context.json pair_rollups.
        nasas_root: Path to the project root, used to shorten file paths.
        generated_at: ISO timestamp string. Defaults to now.
    """
    slug = _project_slug(project_name)
    letter = _project_letter(slug)
    date_str = (generated_at or datetime.now(timezone.utc).isoformat())[:10]
    incidents: list[dict] = primary_payload.get("incidents") or []
    n_incidents = len(incidents)
    n_conflicts = primary_payload.get("incident_conflict_count", 0)

    # ── Header ─────────────────────────────────────────────────────────────────
    lines: list[str] = [
        f"# Guía de Revisión Manual de Clashes — {project_name.split('—')[0].strip()}",
        f"**Generado el:** {date_str}",
        f"**Preparado por:** Sistema de Coordinación Dupla",
        f"**Para:** Arquitecto revisor",
        f"**Modo:** Validación campo a campo en AutoCAD",
        f"",
    ]

    # ── State summary ───────────────────────────────────────────────────────────
    if n_incidents == 0:
        lines += [
            f"## Estado — Sin incidencias primarias",
            f"",
            f"> El análisis completó {len(scheduled_pairs or [])} pares programados y no encontró "
            f"conflictos geométricos entre elementos estructurales primarios (muros, losas, vigas, columnas).",
            f">",
            f"> Esto puede indicar que el proyecto está bien coordinado en las capas detectadas, "
            f"o que las capas estructurales necesitan revisión en la configuración de reglas.",
            f"",
            _INSTRUCTIONS,
            f"## Próximos pasos recomendados",
            f"",
            f"1. Verificar que las capas ARQ y EST estén correctamente nombradas (ver `layer_role_coverage.csv` en la carpeta de salida).",
            f"2. Si el proyecto tiene capas no estándar, agregar reglas en `config/layer_rules/{slug.lower()}.yaml`.",
            f"3. Revisar `pair_schedule_diagnostics.csv` para entender por qué cada par fue o no programado.",
            f"",
        ]
        return "\n".join(lines)

    # ── With incidents ──────────────────────────────────────────────────────────
    lines += [
        f"## Estado — {n_incidents} incidencia(s) primaria(s) · {n_conflicts} conflicto(s)",
        f"",
    ]

    # Group incidents by (layer_a, layer_b) pair
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for inc in incidents:
        key = _layers_from_incident(inc)
        groups[key].append(inc)

    # Build summary table header
    lines += [
        _INSTRUCTIONS,
        f"## Orden de Revisión Recomendado",
        f"",
        f"| # | Grupo | Capas | Incidentes | Área total (m²) | Prioridad |",
        f"|---|---|---|---|---|---|",
    ]

    group_order = sorted(
        groups.items(),
        key=lambda kv: -sum(
            (i.get("representative_conflict") or {}).get("plan_intersection_area_mm2", 0) or 0
            for i in kv[1]
        ),
    )

    group_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    group_meta: list[tuple[str, tuple[str, str], list[dict]]] = []

    for idx, (key, incs) in enumerate(group_order):
        gl = group_letters[idx] if idx < len(group_letters) else str(idx)
        layer_a, layer_b = key
        total_area = sum(
            _area_m2(
                (i.get("representative_conflict") or {}).get("plan_intersection_area_mm2", 0) or 0
            )
            for i in incs
        )
        priority = "**Empieza aquí**" if idx == 0 else ("Revisar" if idx < 3 else "Confirmar rápido")
        lines.append(
            f"| {idx + 1} | {letter}-{gl} | `{layer_a}` / `{layer_b}` "
            f"| {len(incs)} | {total_area} | {priority} |"
        )
        group_meta.append((gl, key, incs))

    lines.append("")
    lines.append("---")

    # ── Per-group sections ──────────────────────────────────────────────────────
    for gl, (layer_a, layer_b), incs in group_meta:
        total_area = sum(
            _area_m2(
                (i.get("representative_conflict") or {}).get("plan_intersection_area_mm2", 0) or 0
            )
            for i in incs
        )
        lines += [
            f"",
            f"## GRUPO {letter}-{gl} — `{layer_a}` vs `{layer_b}`",
            f"",
            f"**{len(incs)} incidente(s)** · Área total acumulada: **{total_area} m²**",
            f"",
        ]

        # Brief group context
        layer_a_low = layer_a.lower()
        layer_b_low = layer_b.lower()
        if any(w in layer_a_low for w in ("marco", "tarjeta", "title")):
            lines.append(
                f"> ⚠️ **`{layer_a}` es probablemente el marco de la hoja de plano.** "
                f"Verifica antes de revisar si esta capa tiene geometría constructiva real o es solo el borde decorativo."
            )
        elif any(w in layer_a_low for w in ("escala", "simbolo", "texto", "dim")):
            lines.append(
                f"> ℹ️ La capa `{layer_a}` suele ser anotación. "
                f"Estos incidentes tienen alta probabilidad de ser falsos positivos."
            )
        lines.append("")

        for i_idx, inc in enumerate(incs):
            code = f"{letter}-{gl}{i_idx + 1}"
            lines.append(_incident_card(inc, code=code, group_label=f"{letter}-{gl}"))

    lines.append("")

    # ── Validation bitácora ─────────────────────────────────────────────────────
    lines += [
        f"---",
        f"",
        f"## Bitácora de Validación — {project_name.split('—')[0].strip()}",
        f"",
        f"*Completa esta tabla a medida que revisas cada punto.*",
        f"",
        f"| Código | Capas | Área (m²) | Decisión | Notas del revisor | Fecha |",
        f"|---|---|---|---|---|---|",
    ]

    for gl, (layer_a, layer_b), incs in group_meta:
        for i_idx, inc in enumerate(incs):
            code = f"{letter}-{gl}{i_idx + 1}"
            inc_id = inc.get("incident_id", "?")
            area_mm2 = (inc.get("representative_conflict") or {}).get(
                "plan_intersection_area_mm2", 0
            ) or 0
            area = _area_m2(area_mm2)
            lines.append(
                f"| {code} (`{inc_id}`) | `{layer_a}` / `{layer_b}` "
                f"| {area} | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |"
            )

    lines += [
        f"",
        f"---",
        f"",
        f"*Reporte generado por Dupla — pipeline 2.5D con roles canónicos y tolerancias explícitas.*",
    ]

    return "\n".join(lines)


def revision_report_filename(project_name: str) -> str:
    """Return the output filename for this project's revision report."""
    slug = _project_slug(project_name)
    return f"REVISION_CLASHES_ARQUITECTO_{slug}.md"


def rebuild_general_revision_report(*, repo_root: Path) -> Path:
    """
    Rebuild REVISION_CLASHES_ARQUITECTO.md from latest per-project revision reports.

    Rules:
    - Source files are REVISION_CLASHES_ARQUITECTO_{PROJECT}.md
    - If there are duplicates for the same PROJECT slug, keep the newest file by mtime
    - Ignore technical/meta reports like REVISION_CLASHES_ARQUITECTO_V2.md
    """
    pattern = "REVISION_CLASHES_ARQUITECTO_*.md"
    newest_by_slug: dict[str, Path] = {}
    for path in repo_root.rglob(pattern):
        match = re.match(r"^REVISION_CLASHES_ARQUITECTO_(.+)\.md$", path.name, flags=re.IGNORECASE)
        if not match:
            continue
        slug = str(match.group(1)).upper()
        if slug in {"V2", "V3", "V4", "FINAL", "GENERAL"}:
            continue
        current = newest_by_slug.get(slug)
        if current is None or path.stat().st_mtime > current.stat().st_mtime:
            newest_by_slug[slug] = path

    generated_at = datetime.now(timezone.utc).isoformat()
    lines: list[str] = [
        "# Guía de Revisión Manual de Clashes — General",
        "**Generado el:** " + generated_at[:10],
        "**Preparado por:** Sistema de Coordinación Dupla",
        "**Modo:** Consolidado por proyecto (automático)",
        "",
    ]

    if not newest_by_slug:
        lines += [
            "## Estado",
            "",
            "No hay reportes por proyecto todavía. Ejecuta una corrida de coordinación para generar el primero.",
            "",
        ]
        out_path = repo_root / "REVISION_CLASHES_ARQUITECTO.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    lines += [
        "## Proyectos incluidos",
        "",
        "| Proyecto | Archivo fuente |",
        "|---|---|",
    ]
    for slug in sorted(newest_by_slug):
        source = newest_by_slug[slug]
        rel = source.relative_to(repo_root).as_posix()
        lines.append(f"| `{slug}` | `{rel}` |")

    lines += [
        "",
        "---",
        "",
        _INSTRUCTIONS,
    ]

    for slug in sorted(newest_by_slug):
        source = newest_by_slug[slug]
        report_text = source.read_text(encoding="utf-8")
        lines += [
            "",
            "---",
            "",
            f"## PROYECTO — {slug}",
            "",
            f"_Fuente: `{source.relative_to(repo_root).as_posix()}`_",
            "",
            report_text,
            "",
        ]

    out_path = repo_root / "REVISION_CLASHES_ARQUITECTO.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_revision_reports(
    *,
    repo_root: Path,
    project_root: Path,
    output_dir: Path,
    project_name: str,
    primary_payload: dict,
    scheduled_pair_count: int = 0,
    generated_at: str | None = None,
) -> tuple[Path, Path, Path]:
    """
    Write the per-project architect report and refresh the global report.

    Returns:
        (project_report_in_output_dir, project_report_in_project_root, general_report_path)
    """
    revision_md_text = render_revision_report(
        project_name=project_name or "Proyecto",
        primary_payload=primary_payload,
        scheduled_pairs=[{}] * max(int(scheduled_pair_count or 0), 0),
        pair_rollups=None,
        nasas_root=project_root,
        generated_at=generated_at,
    )
    revision_filename = revision_report_filename(project_name or "Proyecto")
    out_report = output_dir / revision_filename
    project_report = project_root / revision_filename
    out_report.write_text(revision_md_text, encoding="utf-8")
    project_report.write_text(revision_md_text, encoding="utf-8")
    general_report = rebuild_general_revision_report(repo_root=repo_root)
    return (out_report, project_report, general_report)
