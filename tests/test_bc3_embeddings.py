from pathlib import Path

import numpy as np

from core.schemas import QuantityTakeoff, QuantityTrace
from knowledge.bc3_embeddings import (
    batch_search_bc3,
    build_bc3_embeddings,
    build_query_from_takeoff,
    load_or_build_embeddings,
    search_bc3,
)


def _fake_embed(texts: list[str]) -> np.ndarray:
    vectors = []
    for text in texts:
        lowered = text.lower()
        vectors.append(
            [
                1.0 if "panete" in lowered or "pañete" in lowered else 0.0,
                1.0 if "puerta" in lowered else 0.0,
                1.0 if "piso" in lowered or "porcelanato" in lowered else 0.0,
            ]
        )
    return np.asarray(vectors, dtype=np.float32)


def test_batch_search_bc3_matches_single_search(tmp_path: Path) -> None:
    catalog = {
        "items": [
            {"code": "P0501101", "summary": "Pañete en muros interiores", "long_text": "", "unit": "m2", "price": 8.4},
            {"code": "P1501004", "summary": "Puerta comercial aluminio", "long_text": "", "unit": "u", "price": 424.61},
        ]
    }
    index = build_bc3_embeddings(catalog, embed_batch_fn=_fake_embed, cache_dir=tmp_path)
    queries = ["pañete muros interiores", "puerta aluminio", ""]
    batch = batch_search_bc3(queries, index, top_k=1, embed_batch_fn=_fake_embed)
    assert len(batch) == 3
    assert batch[2] == []
    assert batch[0][0]["code"] == search_bc3(queries[0], index, top_k=1, embed_batch_fn=_fake_embed)[0]["code"]
    assert batch[1][0]["code"] == search_bc3(queries[1], index, top_k=1, embed_batch_fn=_fake_embed)[0]["code"]


def test_build_and_search_bc3_embeddings(tmp_path: Path) -> None:
    catalog = {
        "items": [
            {"code": "P0501101", "summary": "Pañete en muros interiores", "long_text": "", "unit": "m2", "price": 8.4},
            {"code": "P1501004", "summary": "Puerta comercial aluminio", "long_text": "", "unit": "u", "price": 424.61},
        ]
    }

    index = build_bc3_embeddings(catalog, embed_batch_fn=_fake_embed, cache_dir=tmp_path)
    results = search_bc3("pañete muros interiores", index, top_k=1, embed_batch_fn=_fake_embed)

    assert index.vectors.shape[0] == 2
    assert results[0]["code"] == "P0501101"
    assert isinstance(results[0]["score"], float)


def test_load_or_build_embeddings_uses_cache(tmp_path: Path) -> None:
    catalog = {
        "items": [
            {"code": "P0610001", "summary": "Piso porcelanato", "long_text": "", "unit": "m2", "price": 42.32},
        ]
    }
    first = load_or_build_embeddings(catalog, embed_batch_fn=_fake_embed, cache_dir=tmp_path)
    second = load_or_build_embeddings(catalog, embed_batch_fn=None, cache_dir=tmp_path)

    assert first is not None
    assert second is not None
    assert second.metadata[0]["code"] == "P0610001"


def test_build_query_from_takeoff_uses_spanish_mapping() -> None:
    takeoff = QuantityTakeoff(
        item_key="wall-01:finish",
        item_type="wall_finish_plaster",
        unit="m2",
        quantity=100,
        formula="l*h",
        assumptions=["incluye desperdicio"],
        trace=QuantityTrace(evidence=["muro interior"]),
    )
    query = build_query_from_takeoff(takeoff)

    assert "panete en muros interiores" in query
    assert "muro interior" in query
