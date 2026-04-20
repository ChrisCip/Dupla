import json

from analysis.detail_inventory import (
    build_detail_inventory_user_content,
    parse_detail_inventory_json,
)


def test_parse_detail_inventory_json() -> None:
    payload = {
        "discipline": "electrica",
        "explicit_elements": [
            {
                "element_id": "O1",
                "kind": "outlet",
                "label": "Toma 110V",
                "specs": "duplex",
                "location": "Planta 3",
                "count_method": "conteo simbolos",
            }
        ],
        "implicit_elements": [],
        "missing_elements": [],
        "assumptions_needed": [],
    }
    rep = parse_detail_inventory_json(json.dumps(payload))
    assert rep.discipline == "electrica"
    assert rep.explicit_elements[0].element_id == "O1"


def test_build_detail_inventory_user_content_includes_discipline_block() -> None:
    body = build_detail_inventory_user_content("sanitaria")
    assert "sanitaria" in body
    assert "JSON" in body
