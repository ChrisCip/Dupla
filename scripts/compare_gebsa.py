"""
Compare Dupla output BC3 files against the real GEBSA IV BC3.

Usage:
    python scripts/compare_gebsa.py \
        --output data/presupuesto_arquitectura.bc3 \
                 data/presupuesto_estructura.bc3 \
                 data/presupuesto_electrico.bc3 \
                 data/presupuesto_sanitario.bc3 \
        --real data/GIV00001__1_.bc3

Matching is done by description similarity + unit compatibility, NOT by code,
because output and real use different coding schemes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from processors.bc3_parser import parse_bc3


# ---------------------------------------------------------------------------
# Item extraction
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "de", "del", "la", "el", "y", "en", "con", "para", "por", "a", "los", "las",
    "un", "una", "al", "lo", "sin", "sobre", "o", "u",
    "tipo", "seccion", "ubicacion", "varios", "varias", "puntos", "plano",
    "general", "ubicaciones", "rooms", "ceiling", "zona", "este", "central",
    "nivel", "bloque", "caseta", "guardia",
}

# Debug-ish tokens emitted by the pipeline (e.g. "json-wall-cocina") get squashed.
_JSON_TOKEN_RE = re.compile(r"\bjson[-_a-z0-9]+\b", re.IGNORECASE)
_PARENTHETICAL_RE = re.compile(r"\([^)]*\)")


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def _normalize_text(text: str) -> str:
    text = _PARENTHETICAL_RE.sub(" ", text)
    text = _JSON_TOKEN_RE.sub(" ", text)
    text = _strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9\s./\"]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> set[str]:
    return {
        tok for tok in _normalize_text(text).split()
        if tok and tok not in _STOPWORDS and len(tok) > 1
    }


_UNIT_ALIASES = {
    "m3": {"m3", "m³", "mc"},
    "m2": {"m2", "m²"},
    "ml": {"ml", "m", "metro", "mts"},
    "ud": {"ud", "u", "uds", "unidad", "und", "pza", "pieza", "unit", "units"},
    "kg": {"kg", "kgs"},
    "qq": {"qq", "quintal"},
    "lt": {"lt", "l", "litro"},
    "pa": {"pa", "p.a.", "p.a"},
    "h": {"h", "hr", "hora"},
}


def _canonical_unit(unit: str) -> str:
    raw = _strip_accents(unit or "").lower().strip().strip(".")
    for canon, aliases in _UNIT_ALIASES.items():
        if raw in aliases:
            return canon
    return raw


class Item:
    __slots__ = (
        "source", "code", "summary", "unit", "price", "quantity", "amount",
        "norm", "tokens", "canon_unit", "price_source",
    )

    def __init__(
        self,
        source: str,
        code: str,
        summary: str,
        unit: str,
        price: float,
        quantity: float,
        price_source: str = "",
    ) -> None:
        self.source = source
        self.code = code
        self.summary = summary
        self.unit = unit
        self.price = price
        self.quantity = quantity
        self.amount = price * quantity
        self.norm = _normalize_text(summary)
        self.tokens = _tokenize(summary)
        self.canon_unit = _canonical_unit(unit)
        # "constructor_apu" | "bc3_catalog" | "" (unknown)
        self.price_source = price_source


def _quantities_by_item(catalog: dict) -> dict[str, float]:
    """Sum measurement totals per priced item code (cleaning the leading '\\')."""
    qty_by_code: dict[str, float] = {}
    for parent_code, entries in catalog.get("measurements", {}).items():
        for entry in entries:
            child = (entry.get("child") or "").replace("\\", "").strip()
            # Some producers emit ~M with the priced item itself in the parent
            # slot (no child) — accept that form too.
            target = child or (parent_code or "").replace("\\", "").strip()
            if not target:
                continue
            raw = entry.get("raw", "")
            parts = raw.split("|")
            qty = None
            if len(parts) > 1:
                qty_text = parts[1].strip().replace(",", ".")
                try:
                    qty = float(qty_text)
                except ValueError:
                    qty = None
            if qty is None:
                continue
            qty_by_code[target] = qty_by_code.get(target, 0.0) + qty
    return qty_by_code


def _price_source_index(budget_json_path: Path | None) -> dict[str, str]:
    """Map ``BC3 code -> source_type`` from a discipline budget JSON, if available.

    The pipeline writes ``budget_output.json`` per discipline. Each line carries
    ``metadata.source_type`` ("constructor_apu" / "bc3_catalog") when the run
    used ``--pricing-excel``; older runs leave it absent and we infer from the
    ``price_source`` string instead.
    """
    if budget_json_path is None or not budget_json_path.exists():
        return {}
    try:
        payload = json.loads(budget_json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    out: dict[str, str] = {}
    for line in payload.get("lines", []):
        code = str(line.get("code", "") or "").strip()
        if not code:
            continue
        meta = line.get("metadata") or {}
        src = str(meta.get("source_type") or "").strip()
        if not src:
            ps = str(meta.get("price_source") or "")
            if "Constructor APU" in ps:
                src = "constructor_apu"
            elif ps:
                src = "bc3_catalog"
        if src:
            out[code] = src
    return out


def _load_items(
    path: Path,
    source_label: str,
    *,
    budget_json: Path | None = None,
) -> list[Item]:
    catalog = parse_bc3(str(path))
    qty_map = _quantities_by_item(catalog)
    price_src_by_code = _price_source_index(budget_json)
    items: list[Item] = []
    for raw in catalog.get("items", []):
        code = raw.get("code", "")
        summary = (raw.get("summary") or "").strip()
        unit = (raw.get("unit") or "").strip()
        price = float(raw.get("price") or 0.0)
        if not summary or price <= 0:
            continue
        qty = qty_map.get(code, 1.0)
        items.append(Item(
            source_label, code, summary, unit, price, qty,
            price_source=price_src_by_code.get(code, ""),
        ))
    return items


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def _similarity(a: Item, b: Item) -> float:
    if not a.norm or not b.norm:
        return 0.0
    if a.tokens and b.tokens:
        inter = len(a.tokens & b.tokens)
        jaccard = inter / len(a.tokens | b.tokens)
        # Coverage: how much of the shorter side is covered by the other.
        coverage = inter / min(len(a.tokens), len(b.tokens))
    else:
        jaccard = 0.0
        coverage = 0.0
    ratio = SequenceMatcher(None, a.norm, b.norm).ratio()
    return 0.4 * jaccard + 0.3 * coverage + 0.3 * ratio


def _units_compatible(a: Item, b: Item) -> bool:
    if not a.canon_unit or not b.canon_unit:
        return True
    return a.canon_unit == b.canon_unit


def _match_items(
    output_items: list[Item],
    real_items: list[Item],
    *,
    threshold: float = 0.45,
) -> tuple[list[tuple[Item, Item, float]], list[Item], set[int]]:
    """
    Greedy 1:1 matching of output -> real.

    Returns (matches, unmatched_outputs, matched_real_indices).
    """
    matches: list[tuple[Item, Item, float]] = []
    unmatched_out: list[Item] = []
    used_real: set[int] = set()

    real_by_token: dict[str, list[int]] = {}
    for idx, r in enumerate(real_items):
        for tok in r.tokens:
            real_by_token.setdefault(tok, []).append(idx)

    for out in output_items:
        candidate_indices: set[int] = set()
        for tok in out.tokens:
            candidate_indices.update(real_by_token.get(tok, []))
        candidate_indices.difference_update(used_real)
        if not candidate_indices:
            unmatched_out.append(out)
            continue

        best_idx = -1
        best_score = 0.0
        for idx in candidate_indices:
            real = real_items[idx]
            if not _units_compatible(out, real):
                continue
            score = _similarity(out, real)
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx == -1 or best_score < threshold:
            unmatched_out.append(out)
        else:
            matches.append((out, real_items[best_idx], best_score))
            used_real.add(best_idx)

    return matches, unmatched_out, used_real


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _bucket_counts(matches: list[tuple[Item, Item, float]], thresholds: Iterable[float]) -> list[tuple[float, int]]:
    """Cumulative counts of matches whose unit-price delta is within ±threshold."""
    out: list[tuple[float, int]] = []
    for t in thresholds:
        c = 0
        for out_item, real_item, _ in matches:
            if real_item.price <= 0:
                continue
            rel = abs(out_item.price - real_item.price) / real_item.price
            if rel <= t:
                c += 1
        out.append((t, c))
    return out


def _print_report(
    output_items: list[Item],
    real_items: list[Item],
    matches: list[tuple[Item, Item, float]],
    used_real: set[int],
) -> None:
    n_out = len(output_items)
    n_real = len(real_items)
    n_match = len(matches)
    only_out = n_out - n_match
    only_real = n_real - len(used_real)
    pct_match = (n_match / n_real * 100.0) if n_real else 0.0

    print("COMPARACION GEBSA IV - Output vs Real")
    print("=" * 50)
    print()
    print("COBERTURA:")
    print(f"  Partidas output:  {n_out}")
    print(f"  Partidas real:    {n_real}")
    print(f"  Matcheadas:       {n_match} ({pct_match:.1f}% del real)")
    print(f"  Solo en output:   {only_out}")
    print(f"  Solo en real:     {only_real}")
    print()

    if matches:
        pricing_buckets = _bucket_counts(matches, (0.10, 0.25, 0.50))
        print("PRECISION DE PRECIOS (sobre matcheadas):")
        for t, c in pricing_buckets:
            pct = c / n_match * 100.0
            label = f"Dentro de ±{int(t * 100)}%"
            print(f"  {label:<18} {c:4d} ({pct:5.1f}%)")
        outside_50 = n_match - pricing_buckets[-1][1]
        print(f"  {'Fuera de ±50%':<18} {outside_50:4d} ({outside_50 / n_match * 100.0:5.1f}%)")
        print()

        qty_match = [m for m in matches if m[1].quantity > 0 and m[0].quantity > 0]
        if qty_match:
            qty_buckets = []
            for t in (0.10, 0.25, 0.50):
                c = sum(
                    1 for out_item, real_item, _ in qty_match
                    if abs(out_item.quantity - real_item.quantity) / real_item.quantity <= t
                )
                qty_buckets.append((t, c))
            print(f"PRECISION DE CANTIDADES (sobre {len(qty_match)} matcheadas con qty>0):")
            for t, c in qty_buckets:
                pct = c / len(qty_match) * 100.0
                label = f"Dentro de ±{int(t * 100)}%"
                print(f"  {label:<18} {c:4d} ({pct:5.1f}%)")
            outside = len(qty_match) - qty_buckets[-1][1]
            print(f"  {'Fuera de ±50%':<18} {outside:4d} ({outside / len(qty_match) * 100.0:5.1f}%)")
            print()

        deltas = [
            (out_item, real_item, score, out_item.amount - real_item.amount)
            for out_item, real_item, score in matches
        ]
        deltas.sort(key=lambda x: abs(x[3]), reverse=True)
        print("TOP 10 PARTIDAS CON MAYOR DELTA DE IMPORTE:")
        for i, (out_item, real_item, score, delta) in enumerate(deltas[:10], start=1):
            print(f"  {i:2d}. [{score:.2f}] {real_item.summary[:55]}")
            print(
                f"        output: {out_item.amount:>14,.2f}  ({out_item.price:>10,.2f} × {out_item.quantity:>8,.2f} {out_item.unit})"
            )
            print(
                f"        real:   {real_item.amount:>14,.2f}  ({real_item.price:>10,.2f} × {real_item.quantity:>8,.2f} {real_item.unit})"
            )
            print(f"        delta:  {delta:>14,.2f}")
        print()

    print("SOLO EN OUTPUT (primeras 10):")
    for it in output_items[: min(10, n_out)]:
        if not any(it is m[0] for m in matches):
            print(f"  [{it.source}] {it.summary[:80]} ({it.price:,.2f} {it.unit})")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Dupla output BC3 vs real GEBSA BC3")
    parser.add_argument(
        "--output",
        nargs="+",
        required=True,
        help="One or more output BC3 files (per discipline)",
    )
    parser.add_argument(
        "--real",
        required=True,
        help="Real (ground-truth) BC3 file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="Minimum similarity to consider a match (default: 0.35)",
    )
    parser.add_argument(
        "--budget-json",
        nargs="+",
        default=None,
        help="Optional budget_output.json per discipline (parallel order to --output). "
             "Used to extract pricing source_type for the 'Pricing source' section.",
    )
    parser.add_argument(
        "--baseline-v1",
        type=str,
        default=None,
        help="Path to a previous BASELINE_GEBSA_V1.md for delta comparison",
    )
    parser.add_argument(
        "--out-md",
        type=str,
        default=None,
        help="Write the rendered markdown to this path (in addition to stdout)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="BASELINE GEBSA IV - V1",
        help="Markdown H1 title",
    )
    args = parser.parse_args()

    real_path = Path(args.real)
    if not real_path.exists():
        print(f"ERROR: real BC3 not found: {real_path}", file=sys.stderr)
        return 2

    budget_jsons: list[Path | None] = []
    if args.budget_json:
        budget_jsons = [Path(p) if p else None for p in args.budget_json]

    output_items: list[Item] = []
    for idx, p in enumerate(args.output):
        path = Path(p)
        if not path.exists():
            print(f"WARN: output BC3 not found, skipping: {path}", file=sys.stderr)
            continue
        label = path.stem.replace("presupuesto_", "")
        bj = budget_jsons[idx] if idx < len(budget_jsons) else None
        items = _load_items(path, label, budget_json=bj)
        bj_note = f" + {bj.name}" if bj and bj.exists() else ""
        print(f"Loaded output {path.name}{bj_note}: {len(items)} priced items", file=sys.stderr)
        output_items.extend(items)

    if not output_items:
        print("ERROR: no output items loaded", file=sys.stderr)
        return 2

    real_items = _load_items(real_path, "real")
    print(f"Loaded real {real_path.name}: {len(real_items)} priced items", file=sys.stderr)
    print(file=sys.stderr)

    matches, _unmatched, used_real = _match_items(
        output_items, real_items, threshold=args.threshold
    )
    _print_report(output_items, real_items, matches, used_real)

    if args.out_md:
        baseline = _parse_v1_headline(Path(args.baseline_v1)) if args.baseline_v1 else {}
        md = render_markdown(
            output_items, real_items, matches, used_real,
            real_path=str(real_path), output_paths=args.output,
            threshold=args.threshold,
            baseline_v1=baseline,
            title=args.title,
        )
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(md, encoding="utf-8")
        print(f"Wrote {out_md}", file=sys.stderr)
    return 0


def _pricing_breakdown(items: list[Item]) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """Return (overall_counts, per_discipline_counts) keyed by source_type label.

    Output labels: ``"APU Constructor"``, ``"Catálogo BC3"``, ``"(desconocido)"``.
    """
    label_map = {
        "constructor_apu": "APU Constructor",
        "bc3_catalog": "Catálogo BC3",
        "": "(desconocido)",
    }
    overall: Counter[str] = Counter()
    per_disc: dict[str, Counter[str]] = {}
    for it in items:
        label = label_map.get(it.price_source, "(desconocido)")
        overall[label] += 1
        per_disc.setdefault(it.source, Counter())[label] += 1
    return dict(overall), {k: dict(v) for k, v in per_disc.items()}


def _parse_v1_headline(baseline_md: Path | None) -> dict[str, Any]:
    """Extract a few headline numbers from a previous BASELINE_GEBSA_V1.md.

    Best-effort parse — pulls 'Matcheadas', 'Partidas output/real', and the
    bands from the precision tables. Missing values just stay absent.
    """
    out: dict[str, Any] = {}
    if not baseline_md or not baseline_md.exists():
        return out
    text = baseline_md.read_text(encoding="utf-8")
    m = re.search(r"\|\s*Matcheadas\s*\|\s*(\d+)\s*\(([\d.]+)%", text)
    if m:
        out["matched_n"] = int(m.group(1))
        out["matched_pct"] = float(m.group(2))
    m = re.search(r"\|\s*Partidas output\s*\|\s*(\d+)", text)
    if m:
        out["output_n"] = int(m.group(1))
    m = re.search(r"\|\s*Partidas real\s*\|\s*(\d+)", text)
    if m:
        out["real_n"] = int(m.group(1))
    for pct in (10, 25, 50):
        m = re.search(rf"\|\s*Dentro de \+/-{pct}%\s*\|\s*(\d+)\s*\|\s*([\d.]+)%", text)
        if m:
            out[f"price_within_{pct}_n"] = int(m.group(1))
            out[f"price_within_{pct}_pct"] = float(m.group(2))
    return out


def render_markdown(
    output_items: list[Item],
    real_items: list[Item],
    matches: list[tuple[Item, Item, float]],
    used_real: set[int],
    *,
    real_path: str,
    output_paths: list[str],
    threshold: float,
    baseline_v1: dict[str, Any] | None = None,
    title: str = "BASELINE GEBSA IV - V1",
) -> str:
    n_out = len(output_items)
    n_real = len(real_items)
    n_match = len(matches)
    pct_match = (n_match / n_real * 100.0) if n_real else 0.0
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("Comparacion automatica del output del pipeline Dupla contra el BC3 real de GEBSA IV.")
    lines.append("Matching por similitud de descripcion + unidad compatible (no por codigo).")
    lines.append("")
    lines.append("## Fuentes")
    lines.append("")
    lines.append(f"- **Real:** `{real_path}` ({n_real} partidas con precio > 0)")
    lines.append("- **Output:**")
    for p in output_paths:
        lines.append(f"  - `{p}`")
    lines.append(f"- **Threshold de similitud:** {threshold}")
    lines.append("")
    lines.append("## Cobertura")
    lines.append("")
    lines.append("| Metrica | Valor |")
    lines.append("|---|---:|")
    lines.append(f"| Partidas output | {n_out} |")
    lines.append(f"| Partidas real | {n_real} |")
    lines.append(f"| Matcheadas | {n_match} ({pct_match:.1f}% del real) |")
    lines.append(f"| Solo en output | {n_out - n_match} |")
    lines.append(f"| Solo en real | {n_real - len(used_real)} |")
    lines.append("")

    if matches:
        pricing_buckets = _bucket_counts(matches, (0.10, 0.25, 0.50))
        lines.append("## Precision de precios (sobre matcheadas)")
        lines.append("")
        lines.append("| Banda | Partidas | % |")
        lines.append("|---|---:|---:|")
        for t, c in pricing_buckets:
            lines.append(f"| Dentro de +/-{int(t*100)}% | {c} | {c/n_match*100:.1f}% |")
        outside_50 = n_match - pricing_buckets[-1][1]
        lines.append(f"| Fuera de +/-50% | {outside_50} | {outside_50/n_match*100:.1f}% |")
        lines.append("")

        qty_match = [m for m in matches if m[1].quantity > 0 and m[0].quantity > 0]
        if qty_match:
            qty_buckets = []
            for t in (0.10, 0.25, 0.50):
                c = sum(
                    1 for out_item, real_item, _ in qty_match
                    if abs(out_item.quantity - real_item.quantity) / real_item.quantity <= t
                )
                qty_buckets.append((t, c))
            lines.append(f"## Precision de cantidades (sobre {len(qty_match)} matcheadas con qty>0)")
            lines.append("")
            lines.append("| Banda | Partidas | % |")
            lines.append("|---|---:|---:|")
            for t, c in qty_buckets:
                lines.append(f"| Dentro de +/-{int(t*100)}% | {c} | {c/len(qty_match)*100:.1f}% |")
            outside = len(qty_match) - qty_buckets[-1][1]
            lines.append(f"| Fuera de +/-50% | {outside} | {outside/len(qty_match)*100:.1f}% |")
            lines.append("")

        deltas = sorted(
            (
                (out_item, real_item, score, out_item.amount - real_item.amount)
                for out_item, real_item, score in matches
            ),
            key=lambda x: abs(x[3]),
            reverse=True,
        )
        lines.append("## Top 10 partidas con mayor delta de importe")
        lines.append("")
        lines.append("| # | Score | Descripcion (real) | Output (p x q) | Real (p x q) | Delta |")
        lines.append("|---:|---:|---|---|---|---:|")
        for i, (out_item, real_item, score, delta) in enumerate(deltas[:10], start=1):
            lines.append(
                f"| {i} | {score:.2f} | {real_item.summary[:60]} "
                f"| {out_item.price:,.2f} x {out_item.quantity:,.2f} {out_item.unit} "
                f"| {real_item.price:,.2f} x {real_item.quantity:,.2f} {real_item.unit} "
                f"| {delta:,.2f} |"
            )
        lines.append("")

    # --- Pricing source breakdown (Sprint S2 Day 6-8) ---
    overall_src, per_disc_src = _pricing_breakdown(output_items)
    labels_order = ["APU Constructor", "Catálogo BC3", "(desconocido)"]

    apu_count = overall_src.get("APU Constructor", 0)
    if apu_count == 0:
        lines.append("> **Nota:** ninguna partida del output usa precios del constructor.")
        lines.append("> Indica que la corrida es anterior al wiring del APUMatcher,")
        lines.append("> o que se ejecutó sin `--pricing-excel`.")
        lines.append("> Para una V2 real: re-correr `dupla_run_gebsa.py --pricing-excel data\\Lista de precios-analisis-MO.xlsx`.")
        lines.append("")

    lines.append("## Pricing source (origen del precio)")
    lines.append("")
    lines.append("| Fuente | Partidas | % |")
    lines.append("|---|---:|---:|")
    total_src = sum(overall_src.values()) or 1
    for lbl in labels_order:
        n = overall_src.get(lbl, 0)
        if n == 0 and lbl == "(desconocido)":
            continue
        lines.append(f"| {lbl} | {n} | {n/total_src*100:.1f}% |")
    lines.append("")

    if per_disc_src:
        lines.append("### APU match rate por disciplina")
        lines.append("")
        lines.append("| Disciplina | Total | APU Constructor | Catálogo BC3 | Desconocido | Hit APU % |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for disc in sorted(per_disc_src):
            cnts = per_disc_src[disc]
            tot = sum(cnts.values())
            apu = cnts.get("APU Constructor", 0)
            bc3 = cnts.get("Catálogo BC3", 0)
            unk = cnts.get("(desconocido)", 0)
            hit = (apu / tot * 100.0) if tot else 0.0
            lines.append(f"| {disc} | {tot} | {apu} | {bc3} | {unk} | {hit:.1f}% |")
        lines.append("")

    # --- Delta vs baseline V1 ---
    if baseline_v1:
        lines.append("## Delta vs BASELINE V1")
        lines.append("")
        lines.append("| Metrica | V1 | V2 actual | Delta |")
        lines.append("|---|---:|---:|---:|")

        def _row(label: str, v1_key: str, v2_val: float, fmt: str = "{:.1f}") -> None:
            v1 = baseline_v1.get(v1_key)
            if v1 is None:
                return
            delta = v2_val - float(v1)
            lines.append(
                f"| {label} | {fmt.format(float(v1))} | {fmt.format(v2_val)} | "
                f"{'+' if delta >= 0 else ''}{fmt.format(delta)} |"
            )

        n_match = len(matches)
        pct_match = (n_match / max(len(real_items), 1)) * 100.0
        _row("Output items", "output_n", float(len(output_items)), "{:.0f}")
        _row("Real items",   "real_n",   float(len(real_items)),   "{:.0f}")
        _row("Matcheadas (n)", "matched_n", float(n_match), "{:.0f}")
        _row("Matcheadas (%)", "matched_pct", pct_match, "{:.1f}")
        if matches:
            buckets = _bucket_counts(matches, (0.10, 0.25, 0.50))
            for pct, (_, c) in zip((10, 25, 50), buckets):
                cur_pct = (c / n_match * 100.0) if n_match else 0.0
                _row(f"Precios +/-{pct}% (%)", f"price_within_{pct}_pct", cur_pct, "{:.1f}")
        lines.append("")

    lines.append("## Solo en output (primeras 20)")
    lines.append("")
    matched_outs = {id(m[0]) for m in matches}
    unmatched = [it for it in output_items if id(it) not in matched_outs]
    for it in unmatched[:20]:
        ps = f" [{it.price_source}]" if it.price_source else ""
        lines.append(f"- [{it.source}]{ps} {it.summary} (`{it.unit}` @ {it.price:,.2f})")
    lines.append("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
