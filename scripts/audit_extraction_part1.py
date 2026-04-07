"""
Parte 1 — Auditoría de trazabilidad desde dupla_full_budget_output.json

Genera un informe Markdown que separa:
- evidencia CAD (JSON APS normalizado)
- evidencia visión (imágenes / nivel page_*)
- reglas (rules engine → takeoffs expandidos)
- IA (clasificador BC3: gpt4o vs keyword_match)

Uso:
    python scripts/audit_extraction_part1.py --run-dir comparisons/budget/.../2026-04-05_164533
    python scripts/audit_extraction_part1.py --json path/to/dupla_full_budget_output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _find_json(run_dir: Path) -> Path:
    p = run_dir / "dupla_full_budget_output.json"
    if not p.is_file():
        raise FileNotFoundError(f"No está dupla_full_budget_output.json en {run_dir}")
    return p


def _entity_sources(level: dict[str, Any]) -> Counter[str]:
    c: Counter[str] = Counter()
    for key in (
        "walls",
        "openings",
        "doors",
        "windows",
        "wet_areas",
        "kitchens",
        "stairs",
        "fixtures",
        "structural_elements",
    ):
        for ent in level.get(key) or []:
            if isinstance(ent, dict):
                src = str(ent.get("source") or "?")
                c[src] += 1
    return c


def _inventory_section(hybrid: list[dict[str, Any]]) -> tuple[str, list[str]]:
    lines: list[str] = []
    warnings: list[str] = []
    total_conflicts = 0
    for level in hybrid:
        lid = level.get("level_id", "?")
        lname = level.get("level_name", "")
        src = level.get("source", "?")
        lines.append(f"### Nivel `{lid}` — {lname or '(sin nombre)'} — source nivel: `{src}`")
        es = _entity_sources(level)
        if es:
            lines.append("| Entidades por source | Cantidad |")
            lines.append("| --- | ---: |")
            for k, v in sorted(es.items(), key=lambda x: -x[1]):
                lines.append(f"| {k} | {v} |")
        cn = list(level.get("conflict_notes") or [])
        total_conflicts += len(cn)
        if cn:
            lines.append("**Conflictos (CAD vs visión / merge):**")
            for note in cn[:12]:
                lines.append(f"- {note}")
            if len(cn) > 12:
                lines.append(f"- … y {len(cn) - 12} más.")
        lines.append("")
    if total_conflicts:
        warnings.append(f"Hay {total_conflicts} notas de conflicto en inventario: revisar coherencia CAD/visión.")
    return "\n".join(lines), warnings


def _takeoff_row(t: dict[str, Any]) -> str:
    tr = t.get("trace") or {}
    srcs = ", ".join(tr.get("source_entity_sources") or []) or "—"
    n_asum = len(t.get("assumptions") or [])
    return (
        f"| `{t.get('item_key', '')}` | {t.get('item_type', '')} | {t.get('quantity')} | "
        f"{t.get('unit', '')} | {srcs} | {n_asum} |"
    )


def _classifier_source(cands: list[dict[str, Any]]) -> str:
    if not cands:
        return "—"
    top = cands[0]
    return str(top.get("source") or "?")


def _rationale_snippet(r: str, max_len: int = 120) -> str:
    if not r:
        return "—"
    r = r.replace("\n", " ")
    return r if len(r) <= max_len else r[: max_len - 3] + "..."


def build_report(payload: dict[str, Any]) -> str:
    ctx = payload.get("project_context") or {}
    meta = ctx.get("metadata") or {}
    hybrid = payload.get("hybrid_inventory") or []
    takeoffs = payload.get("takeoffs") or []
    base_takeoffs = payload.get("base_takeoffs") or []
    cand_map = payload.get("candidates_by_takeoff") or {}
    diag = payload.get("budget_diagnostics") or {}

    lines: list[str] = [
        "# Auditoría extracción — Parte 1 (trazabilidad)",
        "",
        "## 1. Contexto de corrida",
        "",
        f"- **project_id:** `{ctx.get('project_id', '')}`",
        f"- **plan_image_paths:** {len(ctx.get('plan_image_paths') or [])} imagen(es)",
        f"- **pipeline (inferido):** `{'visión + CAD' if ctx.get('plan_image_paths') else 'solo CAD'}`",
    ]
    if meta.get("vision_pages_dir"):
        lines.append(f"- **vision_pages_dir:** `{meta.get('vision_pages_dir')}`")
    if meta.get("pipeline_mode"):
        lines.append(f"- **pipeline_mode (metadata):** `{meta.get('pipeline_mode')}`")
    lines.append(f"- **dwg_path:** `{meta.get('dwg_path', '—')}`")
    lines.append("")

    lines.append("## 2. Inventario híbrido (origen por entidad)")
    lines.append("")
    inv_md, inv_warn = _inventory_section(hybrid)
    lines.append(inv_md)
    for w in inv_warn:
        lines.append(f"> **Atención:** {w}")
    lines.append("")

    lines.append("## 3. Takeoffs — de dónde sale la cantidad")
    lines.append("")
    lines.append(
        "Reglas (`rules_engine`) expanden takeoffs base; las cantidades vienen de fórmulas sobre inventario "
        "(determinístico salvo supuestos listados)."
    )
    lines.append("")
    lines.append(f"- **Takeoffs base (pre-reglas):** {len(base_takeoffs)}")
    lines.append(f"- **Takeoffs finales (post-reglas):** {len(takeoffs)}")
    lines.append("")
    lines.append("| item_key | item_type | qty | ud | trace sources | #asunciones |")
    lines.append("| --- | --- | ---: | --- | --- | ---: |")
    for t in takeoffs:
        lines.append(_takeoff_row(t))
    lines.append("")

    lines.append("## 4. Compositor de presupuesto (qué entra y qué no)")
    lines.append("")
    if diag:
        lines.append("| Métrica | Valor |")
        lines.append("| --- | ---: |")
        for k, v in sorted(diag.items()):
            if k in ("excluded_by_reason", "excluded_top_item_types"):
                continue
            lines.append(f"| {k} | {v} |")
        ebr = diag.get("excluded_by_reason") or {}
        if ebr:
            lines.append("")
            lines.append("**Excluidos por razón:**")
            for reason, count in sorted(ebr.items(), key=lambda x: -x[1]):
                lines.append(f"- `{reason}`: {count}")
        ett = diag.get("excluded_top_item_types") or {}
        if ett:
            lines.append("")
            lines.append("**Tipos excluidos (top):**")
            for it, count in sorted(ett.items(), key=lambda x: -x[1])[:15]:
                lines.append(f"- `{it}`: {count}")
    else:
        lines.append("_Sin `budget_diagnostics` en el JSON (corrida antigua?)._")
    lines.append("")

    lines.append("## 5. Clasificador BC3 (IA vs determinístico)")
    lines.append("")
    lines.append(
        "- **gpt4o:** clasificación por capítulo con GPT-4o sobre subconjunto BC3 (requiere `OPENAI_API_KEY`)."
    )
    lines.append(
        "- **keyword_match:** ranking por solapamiento de tokens con el catálogo (fallback si no hay GPT o falla)."
    )
    lines.append("")
    lines.append("| takeoff_key | Candidato top | source | rationale (recorte) |")
    lines.append("| --- | --- | --- | --- |")
    for t in takeoffs:
        key = t.get("item_key", "")
        cands = cand_map.get(key) or []
        top = (cands[0] if cands else {}) or {}
        code = top.get("bc3_code", "—")
        src = _classifier_source(cands)
        rat = _rationale_snippet(str(top.get("rationale") or ""))
        lines.append(f"| `{key}` | `{code}` | `{src}` | {rat} |")
    lines.append("")

    lines.append("## 6. Cómo saber si la extracción es “la mejor posible” (Parte 1)")
    lines.append("")
    lines.append(
        "1. **CAD:** revisá que `normalized.json` y el inventario `json`/`hybrid` reflejen capas y geometría esperables."
    )
    lines.append(
        "2. **Visión:** si hay `plan_image_paths`, revisá que `conflict_notes` tengan sentido (no silenciar diferencias)."
    )
    lines.append(
        "3. **Reglas:** si muchos takeoffs quedan excluidos por `derived_child` o `type_excluded`, es el diseño del compositor, no un bug de APS."
    )
    lines.append(
        "4. **IA:** si `source` es `keyword_match` en casi todo, el GPT no está actuando o falló (ver logs)."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoría Parte 1 — trazabilidad desde JSON de corrida")
    parser.add_argument("--run-dir", type=str, default="", help="Carpeta que contiene dupla_full_budget_output.json")
    parser.add_argument("--json", type=str, default="", help="Ruta directa al JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="",
        help="Salida .md (por defecto: run-dir/auditoria_extraccion_parte1.md)",
    )
    args = parser.parse_args()

    if args.json:
        json_path = Path(args.json).resolve()
    elif args.run_dir:
        json_path = _find_json(Path(args.run_dir).resolve())
    else:
        print("Indica --run-dir o --json", file=sys.stderr)
        return 1

    if not json_path.is_file():
        print(f"No existe: {json_path}", file=sys.stderr)
        return 1

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    report = build_report(payload)

    out = Path(args.output).resolve() if args.output else json_path.parent / "auditoria_extraccion_parte1.md"
    out.write_text(report, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
