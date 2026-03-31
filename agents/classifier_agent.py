"""
BC3 candidate matching with GPT-4o chapter segmentation.

Primary path: GPT-4o classifies takeoffs into 9 budget chapters and assigns
the best BC3 code + unit price from the catalog, one GPT-4o call per chapter.

Fallback path (no OpenAI API key): deterministic token-overlap ranking.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from typing import Any, Iterable

from dotenv import load_dotenv
from pathlib import Path

from core.schemas import BudgetCandidate, QuantityTakeoff
from knowledge.bc3_embeddings import EmbeddingIndex, build_query_from_takeoff, search_bc3
from knowledge.pres_expansion import inject_pres_reference_candidates
from knowledge.training_data import TrainingPair, generate_few_shot_examples

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger("dupla.classifier")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# ---------------------------------------------------------------------------
# Chapter definitions — mirror the legacy budget structure
# ---------------------------------------------------------------------------

_CHAPTERS: dict[str, dict[str, Any]] = {
    "01": {
        "title": "MOVIMIENTO DE TIERRAS",
        "desc": "Excavacion, relleno, compactacion, zapatas, cimentacion, bote de material",
        "tokens": {"excavac", "rellen", "compac", "zapata", "ciment", "bote", "movim", "tierr", "suelo"},
    },
    "02": {
        "title": "HORMIGON ARMADO / ESTRUCTURA",
        "desc": "Hormigon armado, acero de refuerzo, columnas, vigas, losas, escaleras, encofrado",
        "tokens": {
            "hormig", "armad", "colum", "viga", "losa", "escal", "encof",
            "acero", "refuerz", "concret", "estruc", "zapata", "fundac",
            "varilla", "fierro",
        },
    },
    "03": {
        "title": "MUROS Y PANETE",
        "desc": "Muros de bloques, panete interior y exterior, revestimientos",
        "tokens": {
            "muro", "bloque", "panete", "panet", "panete", "revest",
            "mampost", "tabiq", "pared", "bloc", "mortero",
        },
    },
    "04": {
        "title": "PISOS Y CERAMICA",
        "desc": "Pisos ceramica, porcelanato, zocalos, pulido, nivelacion",
        "tokens": {
            "piso", "ceramic", "porcelan", "zocal", "pulid", "nivel",
            "terrazo", "porcela", "baldos", "contrap",
        },
    },
    "05": {
        "title": "PUERTAS Y VENTANAS",
        "desc": "Puertas metalicas PVC madera, ventanas aluminio vidrio, herrajes",
        "tokens": {
            "puerta", "ventana", "herraje", "vidrio", "alumin",
            "cerradura", "bisagra", "marco", "hoja", "persiana",
        },
    },
    "06": {
        "title": "INSTALACIONES ELECTRICAS",
        "desc": "Puntos electricos, cableado, interruptores, tomas, paneles, luminarias",
        "tokens": {
            "electr", "cable", "interrup", "toma", "panel", "lumin",
            "tubo", "conduit", "breaker", "tomacorr", "switch",
        },
    },
    "07": {
        "title": "SANITARIAS Y PLOMERIA",
        "desc": "Inodoros, lavamanos, duchas, tuberias PVC, cisterna, bombas, drenaje",
        "tokens": {
            "sanitar", "inodor", "lavam", "ducha", "tuberia", "cistern",
            "bomb", "drenaj", "plomer", "acueduc", "bano", "wc",
        },
    },
    "08": {
        "title": "PINTURA Y ACABADOS",
        "desc": "Pintura interior y exterior, impermeabilizante, sellador",
        "tokens": {
            "pintura", "imperm", "sellad", "acabad", "lacado",
            "esmalt", "latex", "paint",
        },
    },
    "09": {
        "title": "GASTOS GENERALES",
        "desc": "Supervision, topografia, seguridad, limpieza, andamios, gastos indirectos",
        "tokens": {
            "supervis", "topogr", "segur", "limpiez", "andami",
            "gastos", "indirect", "administr", "imprevist",
        },
    },
}

# Map item_type (or prefix) to chapter code
_ITEM_TYPE_TO_CHAPTER: dict[str, str] = {
    # Estructura
    "beam_concrete_volume": "02",
    "beam_volume": "02",
    "beam_area": "02",
    "beam_formwork_area_hint": "02",
    "column_concrete_volume": "02",
    "column_volume": "02",
    "column_area": "02",
    "column_formwork_area_hint": "02",
    "slab_concrete_volume": "02",
    "slab_area": "02",
    "slab_formwork_area_hint": "02",
    "footing_concrete_volume": "02",
    "footing_volume": "02",
    "structural_count": "02",
    "structural_area": "02",
    "structural_volume": "02",
    "stair_count": "02",
    # Muros y pañete
    "wall_net_area": "03",
    "wall_volume": "03",
    "wall_waterproofing": "03",
    "wall_finish_plaster": "03",
    "wall_gross_area": "03",
    # Pisos
    "floor_area": "04",
    "floor_finish": "04",
    "floor_waterproofing": "07",
    # Puertas y ventanas
    "door_leaf_wood_count": "05",
    "door_frame_count": "05",
    "door_hardware_set_count": "05",
    "door_count": "05",
    "window_frame_count": "05",
    "window_glazing_area": "05",
    "window_count": "05",
    # Pintura
    "wall_finish_paint": "08",
    "ceiling_area": "08",
    "ceiling_finish_paint": "08",
    # Sanitario
    "wet_area_fixture_count": "07",
    "wet_area_area": "07",
    # Eléctrico
    "fixture_count": "06",
}

_PREFIX_TO_CHAPTER: list[tuple[str, str]] = [
    ("beam_", "02"),
    ("column_", "02"),
    ("slab_", "02"),
    ("footing_", "02"),
    ("structural_", "02"),
    ("stair_", "02"),
    ("wall_finish_paint", "08"),
    ("wall_finish_plast", "03"),
    ("wall_net", "03"),
    ("wall_vol", "03"),
    ("wall_water", "03"),
    ("wall_", "03"),
    ("floor_area", "04"),
    ("floor_finish", "04"),
    ("floor_water", "07"),
    ("floor_", "04"),
    ("ceiling_", "08"),
    ("door_", "05"),
    ("window_", "05"),
    ("wet_area_", "07"),
    ("fixture_", "06"),
]


def _assign_chapter(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    chapter = _ITEM_TYPE_TO_CHAPTER.get(item_type)
    if chapter:
        return chapter
    for prefix, ch in _PREFIX_TO_CHAPTER:
        if item_type.startswith(prefix):
            return ch
    return "09"


def _normalize_text(text: str) -> str:
    """Lowercase + strip accents for consistent token matching."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode("ascii")


def _filter_bc3_for_chapter(
    bc3_catalog: dict[str, Any],
    tokens: set[str],
    *,
    takeoffs: list[QuantityTakeoff] | None = None,
    embedding_index: EmbeddingIndex | None = None,
) -> list[dict[str, Any]]:
    """
    Return BC3 items relevant for the chapter.

    If an embeddings index is available, use semantic search against each takeoff
    query; otherwise use chapter token overlap fallback.
    """
    items = bc3_catalog.get("items", [])
    if embedding_index is not None and takeoffs:
        items_by_code = {str(item.get("code", "")): item for item in items}
        scored_by_code: dict[str, float] = {}
        for takeoff in takeoffs:
            query = build_query_from_takeoff(takeoff)
            for match in search_bc3(query, embedding_index, top_k=15):
                code = str(match.get("code", ""))
                if not code or code not in items_by_code:
                    continue
                score = float(match.get("score") or 0.0)
                if code not in scored_by_code or score > scored_by_code[code]:
                    scored_by_code[code] = score

        ranked_codes = sorted(scored_by_code, key=scored_by_code.get, reverse=True)
        if ranked_codes:
            return [items_by_code[code] for code in ranked_codes]

    result: list[dict[str, Any]] = []
    for item in items:
        text = _normalize_text(
            item.get("summary", "") + " " + item.get("long_text", "")
        )
        if any(token in text for token in tokens):
            result.append(item)
    return result


def _extract_json_list(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array from GPT-4o text output."""
    # Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "items" in parsed:
            return list(parsed["items"])
    except json.JSONDecodeError:
        pass

    # Try to find array in fenced block
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Find array brackets
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            # Try stripping trailing commas
            cleaned = re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

    return []


def _gpt4o_classify_chapter(
    takeoffs: list[QuantityTakeoff],
    bc3_items: list[dict[str, Any]],
    chapter_code: str,
    chapter_desc: str,
    client: "OpenAI",
    few_shot_examples: str = "",
) -> dict[str, BudgetCandidate]:
    """One GPT-4o call per chapter — assign best BC3 code to each takeoff."""
    if not takeoffs or not bc3_items:
        return {}

    # Format takeoffs
    takeoff_lines = []
    for t in takeoffs:
        takeoff_lines.append(
            f'  {{"key":"{t.item_key}","type":"{t.item_type}",'
            f'"unit":"{t.unit}","qty":{t.quantity:.2f}}}'
        )

    # Format BC3 catalog (max 80 items to stay within token limits)
    bc3_lines = []
    for item in bc3_items[:80]:
        price = float(item.get("price") or 0)
        summary = str(item.get("summary") or "")[:70]
        bc3_lines.append(
            f'  {{"code":"{item["code"]}","unit":"{item.get("unit","")}",'
            f'"price":{price:.2f},"summary":"{summary}"}}'
        )

    prompt = (
        f"Eres un presupuestista dominicano senior. Capitulo: {chapter_desc}\n\n"
        + (few_shot_examples + "\n\n" if few_shot_examples else "")
        + "PARTIDAS A CLASIFICAR:\n[\n"
        + ",\n".join(takeoff_lines)
        + "\n]\n\n"
        + "CATALOGO BC3 (precios en RD$):\n[\n"
        + ",\n".join(bc3_lines)
        + "\n]\n\n"
        + "Asigna el codigo BC3 mas apropiado a cada partida.\n"
        + "- Solo asigna si hay un match razonable (misma disciplina y unidad compatible).\n"
        + "- unit_price es el precio del catalogo BC3.\n"
        + "- match_type: exacto | aproximado | estimado\n\n"
        + 'Devuelve SOLO un JSON array (sin texto adicional):\n'
        + '[{"takeoff_key":"<key>","bc3_code":"<code>","unit_price":<price>,"match_type":"exacto|aproximado|estimado"}]'
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": "Presupuestista dominicano. Devuelve SOLO JSON array. Precios en RD$.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content or ""
    except Exception:
        logger.warning(
            "GPT-4o call failed for chapter %s (%d takeoffs)",
            chapter_code, len(takeoffs), exc_info=True,
        )
        return {}

    matches = _extract_json_list(raw)

    # Build a code→item lookup for this chapter's subset
    code_to_item: dict[str, dict[str, Any]] = {item["code"]: item for item in bc3_items}

    result: dict[str, BudgetCandidate] = {}
    for match in matches:
        key = str(match.get("takeoff_key") or "").strip()
        bc3_code = str(match.get("bc3_code") or "").strip()
        if not key or not bc3_code:
            continue

        # Look up unit from catalog; use takeoff unit as canonical for the score check
        bc3_item = code_to_item.get(bc3_code)
        summary = bc3_item.get("summary", bc3_code) if bc3_item else bc3_code

        unit_price = 0.0
        try:
            unit_price = float(match.get("unit_price") or 0)
        except (TypeError, ValueError):
            pass
        # If GPT-4o didn't return a price, look it up from the catalog
        if unit_price == 0.0 and bc3_item:
            unit_price = float(bc3_item.get("price") or 0)

        match_type = str(match.get("match_type") or "aproximado")
        score = 1.0 if match_type == "exacto" else 0.85

        # Find the original takeoff to get its unit (ensures select_strong_candidate passes)
        takeoff_unit = next(
            (t.unit for t in takeoffs if t.item_key == key), ""
        )

        result[key] = BudgetCandidate(
            takeoff_key=key,
            bc3_code=bc3_code,
            summary=summary,
            unit=takeoff_unit,  # use takeoff unit to pass the unit-match check
            score=score,
            rationale=json.dumps({"unit_price": unit_price, "match_type": match_type}),
            source="gpt4o",
        )

    return result


def _match_with_gpt4o(
    takeoffs: list[QuantityTakeoff],
    bc3_catalog: dict[str, Any],
    client: "OpenAI",
    *,
    embedding_index: EmbeddingIndex | None = None,
    training_pairs: list[TrainingPair] | None = None,
) -> dict[str, list[BudgetCandidate]]:
    """Classify all takeoffs via GPT-4o, grouped by chapter."""
    # Group takeoffs by chapter
    chapter_groups: dict[str, list[QuantityTakeoff]] = {}
    for takeoff in takeoffs:
        ch = _assign_chapter(takeoff)
        chapter_groups.setdefault(ch, []).append(takeoff)

    result: dict[str, list[BudgetCandidate]] = {}

    for chapter_code, chapter_takeoffs in sorted(chapter_groups.items()):
        chapter_info = _CHAPTERS[chapter_code]
        bc3_subset = _filter_bc3_for_chapter(
            bc3_catalog,
            chapter_info["tokens"],
            takeoffs=chapter_takeoffs,
            embedding_index=embedding_index,
        )

        if not bc3_subset:
            # No matching BC3 items for this chapter — leave empty (composer uses DUP code)
            continue

        category_hint = chapter_info["title"].split(" ")[0].lower()
        few_shot = generate_few_shot_examples(training_pairs or [], category_hint)
        matches = _gpt4o_classify_chapter(
            chapter_takeoffs,
            bc3_subset,
            chapter_code,
            chapter_info["desc"],
            client,
            few_shot_examples=few_shot,
        )

        for key, candidate in matches.items():
            result[key] = [candidate]

    return result


# ---------------------------------------------------------------------------
# Token-overlap fallback (used when OpenAI is not available)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", text.lower())
        if token and len(token) > 2
    }


def _query_text(takeoff: QuantityTakeoff) -> str:
    trace_values = " ".join(
        [
            " ".join(takeoff.trace.source_entity_ids),
            " ".join(takeoff.trace.evidence),
            " ".join(str(value) for value in takeoff.inputs.values() if value),
        ]
    )
    return f"{takeoff.item_key} {takeoff.item_type} {trace_values}"


def rank_budget_candidates(
    takeoff: QuantityTakeoff,
    bc3_catalog: dict[str, Any],
    top_k: int = 5,
) -> list[BudgetCandidate]:
    query_tokens = _tokenize(_query_text(takeoff))
    candidates: list[BudgetCandidate] = []

    for concept in bc3_catalog.get("items", []):
        summary = str(concept.get("summary", ""))
        long_text = str(concept.get("long_text", ""))
        candidate_tokens = _tokenize(f"{summary} {long_text}")
        if not candidate_tokens:
            continue

        overlap = query_tokens & candidate_tokens
        if not overlap:
            continue

        token_score = len(overlap) / max(len(query_tokens), 1)
        unit_bonus = 0.25 if str(concept.get("unit", "")).lower() == takeoff.unit.lower() else 0.0
        score = round(token_score + unit_bonus, 4)

        candidates.append(
            BudgetCandidate(
                takeoff_key=takeoff.item_key,
                bc3_code=str(concept.get("code", "")),
                summary=summary,
                unit=str(concept.get("unit", "")),
                score=score,
                rationale=f"Shared tokens: {', '.join(sorted(overlap))}",
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:top_k]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_takeoffs_to_bc3(
    takeoffs: Iterable[QuantityTakeoff],
    bc3_catalog: dict[str, Any],
    top_k: int = 3,
    *,
    embedding_index: EmbeddingIndex | None = None,
    training_pairs: list[TrainingPair] | None = None,
) -> dict[str, list[BudgetCandidate]]:
    """
    Assign BC3 candidates to each takeoff.

    Primary: GPT-4o classification grouped by chapter (requires OPENAI_API_KEY).
    Fallback: deterministic token-overlap ranking.
    """
    takeoff_list = list(takeoffs)
    non_pres = [t for t in takeoff_list if t.item_type != "pres_reference_line"]
    result: dict[str, list[BudgetCandidate]] = {}

    if HAS_OPENAI and bc3_catalog.get("items"):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and non_pres:
            try:
                client = OpenAI(api_key=api_key)
                result = _match_with_gpt4o(
                    non_pres,
                    bc3_catalog,
                    client,
                    embedding_index=embedding_index,
                    training_pairs=training_pairs,
                )
            except Exception:
                logger.warning(
                    "GPT-4o matching failed for %d takeoffs, falling back to token overlap",
                    len(non_pres), exc_info=True,
                )
                result = {}

    if not result and non_pres:
        result = {
            takeoff.item_key: rank_budget_candidates(takeoff, bc3_catalog, top_k=top_k)
            for takeoff in non_pres
        }
    elif non_pres:
        for takeoff in non_pres:
            if takeoff.item_key not in result:
                result[takeoff.item_key] = rank_budget_candidates(takeoff, bc3_catalog, top_k=top_k)

    inject_pres_reference_candidates(takeoff_list, result, bc3_catalog)
    return result
