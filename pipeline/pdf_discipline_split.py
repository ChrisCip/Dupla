"""
Clasificación de páginas de un PDF combinado (planos) por disciplina vía GPT-4o visión,
y generación de sub-PDFs por disciplina para correr visión/presupuesto con el perfil adecuado.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from budget.discipline_mapping import GENERAL, normalize_discipline_key

logger = logging.getLogger("dupla.pdf_split")

_DISCIPLINE_PROMPT = """Eres un clasificador de planillas de obra (Rep. Dominicana / internacional).
Miras UNA sola imagen de plano (puede ser portada, detalle, planta, corte, esquema).

Devuelve SOLO un JSON válido (sin markdown) con exactamente estas claves:
- "discipline": una de: structural, electrical, sanitary, finishes_architectural, general
- "title": título corto inferido (ej. "PLANTA ELECTRICA P3") o cadena vacía si no hay título claro

Criterios:
- structural: columnas armadas, vigas, losas, zapatas, detalles de hormigón/acero estructural.
- electrical: luminarias, tomacorrientes, tableros, diagramas unifilares eléctricos.
- sanitary: agua, desagüe, sanitarios como red (no solo icono aislado en arquitectura).
- finishes_architectural: arquitectónico, acabados, pañetes, puertas/ventanas en planta arq., fachadas.
- general: portadas, índices, notas generales, detalles mixtos sin predominio claro."""


def _encode_image_b64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def _extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return {}


def _vision_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("openai package required") from exc
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=key)


@dataclass
class PageDiscipline:
    page_index: int  # 0-based
    discipline: str
    title: str


def render_pdf_page_pngs(
    pdf_path: Path,
    out_dir: Path,
    *,
    dpi: int = 110,
    page_indices: list[int] | None = None,
) -> list[Path]:
    """Renderiza páginas a PNG; por defecto todas. Devuelve rutas ordenadas por índice."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("PyMuPDF (pymupdf) is required") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    indices = page_indices if page_indices is not None else list(range(len(doc)))
    paths: list[Path] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for i in indices:
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        p = out_dir / f"classify_page_{i + 1:04d}.png"
        pix.save(str(p))
        paths.append(p)
    doc.close()
    return paths


def classify_single_page_png(
    png_path: Path,
    *,
    model: str = "gpt-4o",
    low_detail: bool = True,
) -> tuple[str, str]:
    client = _vision_client()
    b64 = _encode_image_b64(png_path)
    ext = png_path.suffix.lower().replace(".", "")
    mime = f"image/{ext}" if ext in {"png", "jpg", "jpeg", "webp"} else "image/png"

    detail = "low" if low_detail else "high"
    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=300,
        messages=[
            {"role": "system", "content": _DISCIPLINE_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Clasifica esta única lámina."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": detail},
                    },
                ],
            },
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = _extract_json_object(raw)
    disc = normalize_discipline_key(str(data.get("discipline", GENERAL)))
    title = str(data.get("title", "") or "").strip()[:200]
    return disc, title


def classify_pdf_pages(
    pdf_path: Path,
    work_dir: Path,
    *,
    dpi: int = 110,
    delay_seconds: float = 0.15,
    model: str = "gpt-4o",
) -> list[PageDiscipline]:
    """
    Clasifica cada página del PDF con GPT-4o visión (una llamada por página).
    Guarda thumbnails y un JSON con el resultado.
    """
    pdf_path = pdf_path.resolve()
    work_dir = work_dir.resolve()
    thumbs = work_dir / "classify_thumbs"
    image_paths = render_pdf_page_pngs(pdf_path, thumbs, dpi=dpi)
    results: list[PageDiscipline] = []
    for idx, img in enumerate(image_paths):
        if delay_seconds > 0 and idx > 0:
            time.sleep(delay_seconds)
        disc, title = classify_single_page_png(img, model=model)
        row = PageDiscipline(page_index=idx, discipline=disc, title=title)
        results.append(row)
        logger.info("Página %d/%d → %s (%s)", idx + 1, len(image_paths), disc, title[:60])

    report = {
        "pdf": str(pdf_path),
        "dpi": dpi,
        "model": model,
        "pages": [
            {"page": r.page_index + 1, "discipline": r.discipline, "title": r.title} for r in results
        ],
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "page_disciplines.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return results


def write_split_pdfs_by_discipline(
    pdf_path: Path,
    labels: list[PageDiscipline],
    out_dir: Path,
) -> dict[str, Path]:
    """
    Escribe un PDF por disciplina (solo páginas clasificadas así), orden conservado.
    Omite disciplinas sin páginas.
    """
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF required") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    by_disc: dict[str, list[int]] = {}
    for row in labels:
        by_disc.setdefault(row.discipline, []).append(row.page_index)

    written: dict[str, Path] = {}
    src = fitz.open(pdf_path)
    try:
        for disc, indices in by_disc.items():
            if not indices:
                continue
            sub = fitz.open()
            for i in sorted(set(indices)):
                if 0 <= i < len(src):
                    sub.insert_pdf(src, from_page=i, to_page=i)
            if len(sub) == 0:
                sub.close()
                continue
            out_p = out_dir / f"split_{disc}.pdf"
            sub.save(str(out_p))
            sub.close()
            written[disc] = out_p.resolve()
            logger.info("PDF disciplina %s: %d páginas → %s", disc, len(indices), out_p)
    finally:
        src.close()
    return written
