"""
Informe de calidad (IA) + PDF simple para corridas NASAS: métricas vs presupuesto real,
brechas de entrada, coherencia cualitativa con extractos de reglamentos MIVED.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("dupla.nasas_quality_report")


def extract_reglamentos_excerpt(reg_dir: Path, *, max_chars: int = 10000) -> str:
    """Texto plano de los primeros PDFs de reglamentos (sin OCR)."""
    import fitz

    chunks: list[str] = []
    total = 0
    for pdf in sorted(reg_dir.glob("*.pdf"))[:12]:
        try:
            with fitz.open(pdf) as doc:
                for page in doc:
                    t = page.get_text() or ""
                    if t.strip():
                        chunks.append(f"--- {pdf.name} p.{page.number + 1} ---\n{t}")
                        total += len(t)
                    if total >= max_chars:
                        break
        except Exception as exc:
            logger.warning("No se pudo leer %s: %s", pdf, exc)
        if total >= max_chars:
            break
    text = "\n".join(chunks)
    return text[:max_chars]


def call_openai_quality_narrative(
    *,
    corrida_name: str,
    corrida_inputs: dict[str, Any],
    comparison_stats: dict[str, Any],
    discipline_json: dict[str, Any] | None,
    reglamentos_excerpt: str,
) -> dict[str, Any]:
    """Devuelve dict JSON con narrativa y puntuaciones (requiere OPENAI_API_KEY)."""
    from openai import OpenAI

    client = OpenAI()
    prompt = f"""Eres un ingeniero de costos y arquitecto revisando un presupuesto generado por software
frente al presupuesto preliminar real del mismo proyecto (NASAS 09, República Dominicana).

Corrida: {corrida_name}
Entradas usadas (JSON): {json.dumps(corrida_inputs, ensure_ascii=False)[:4000]}

Métricas automáticas de comparación Excel (códigos coincidentes, totales, cobertura):
{json.dumps(comparison_stats, ensure_ascii=False)[:6000]}

Desglose por disciplina (si existe):
{json.dumps(discipline_json or {}, ensure_ascii=False)[:4000]}

Extracto de reglamentos MIVED (referencia normativa; puede estar truncado):
{reglamentos_excerpt[:8000]}

Responde SOLO con un objeto JSON válido con estas claves:
- confidence_0_100: número entero 0-100 (qué tan creíble es el presupuesto generado frente al real y a la norma)
- confidence_label: una de "alta", "media", "baja"
- precision_notes: texto breve explicando el porcentaje
- input_gaps: lista de strings (qué faltó en planos/pliego/revisión para un mejor resultado)
- inconsistencies: lista de strings (contradicciones o anomalías entre generado y real o internas)
- regulatory_notes: lista de strings (alineación o riesgos respecto a reglamentos, sin inventar citas exactas si no están en el extracto)
- suggested_fixes: lista de strings accionables para mejorar la siguiente corrida
- web_research_suggestions: lista de temas a buscar en la web oficial MIVED u organismos competentes (no simules URLs)

Sé concreto y en español técnico latinoamericano."""

    response = client.chat.completions.create(
        model=os.environ.get("DUPLA_QUALITY_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    raw = (response.choices[0].message.content or "").strip()
    return json.loads(raw)


def write_quality_pdf(
    output_path: Path,
    *,
    title: str,
    corrida_name: str,
    comparison_md_path: Path | None,
    ai_payload: dict[str, Any] | None,
    extra_sections: list[tuple[str, str]] | None = None,
) -> Path:
    """PDF multipágina con texto (PyMuPDF)."""
    import fitz

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    margin = 48
    fontsize = 10
    page_w, page_h = fitz.paper_rect("a4")
    rect = fitz.Rect(margin, margin, page_w - margin, page_h - margin)

    blocks: list[str] = [
        title,
        "",
        f"Corrida: {corrida_name}",
        "",
    ]
    if ai_payload:
        blocks.append("=== Evaluación IA (coherencia y confianza) ===")
        blocks.append(
            f"Confianza: {ai_payload.get('confidence_0_100', '—')} / 100 "
            f"({ai_payload.get('confidence_label', '—')})"
        )
        blocks.append(ai_payload.get("precision_notes", "") or "")
        blocks.append("")
        for key, label in (
            ("input_gaps", "Brechas de entrada"),
            ("inconsistencies", "Inconsistencias"),
            ("regulatory_notes", "Normativa / reglamentos"),
            ("suggested_fixes", "Mejoras sugeridas"),
            ("web_research_suggestions", "Temas para buscar en web oficial"),
        ):
            items = ai_payload.get(key)
            if not items:
                continue
            blocks.append(f"--- {label} ---")
            if isinstance(items, list):
                blocks.extend(f"• {x}" for x in items[:40])
            else:
                blocks.append(str(items))
            blocks.append("")
    if extra_sections:
        for heading, body in extra_sections:
            blocks.append(f"=== {heading} ===")
            blocks.append(body)
            blocks.append("")
    if comparison_md_path and comparison_md_path.is_file():
        blocks.append("=== Comparación automática (resumen) ===")
        blocks.append(comparison_md_path.read_text(encoding="utf-8")[:12000])

    full = "\n".join(blocks)
    remaining = full
    while remaining.strip():
        page = doc.new_page(width=page_w, height=page_h)
        block, remaining = _split_for_textbox(remaining, rect, fontsize)
        page.insert_textbox(
            rect,
            block,
            fontsize=fontsize,
            fontname="helv",
            align=fitz.TEXT_ALIGN_LEFT,
        )
    doc.save(str(output_path))
    doc.close()
    return output_path.resolve()


def _split_for_textbox(text: str, rect, fontsize: float) -> tuple[str, str]:
    approx = int(rect.width * rect.height / (fontsize * fontsize * 0.5))
    approx = max(1500, approx)
    if len(text) <= approx:
        return text, ""
    cut = text.rfind("\n\n", 0, approx)
    if cut < approx // 3:
        cut = text.rfind("\n", 0, approx)
    if cut < approx // 3:
        cut = approx
    return text[:cut].rstrip(), text[cut:].lstrip()


def export_bc3_from_budget_json(budget_json: Path, output_bc3: Path) -> Path | None:
    """Genera BC3 (Presto) desde dupla_full_budget_output.json."""
    from budget.export_bc3 import export_budget_bc3
    from core.schemas import project_context_from_dict

    data = json.loads(budget_json.read_text(encoding="utf-8"))
    rows = data.get("rows")
    pc = data.get("project_context")
    if not rows or not pc:
        logger.warning("budget JSON sin rows/project_context; no BC3")
        return None
    ctx = project_context_from_dict(pc)
    return export_budget_bc3(ctx, rows, output_bc3)
