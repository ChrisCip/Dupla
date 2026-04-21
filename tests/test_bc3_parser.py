from pathlib import Path

from processors.bc3_parser import parse_bc3


def test_parse_bc3_reads_items_and_texts(tmp_path: Path) -> None:
    bc3_path = tmp_path / "sample.bc3"
    bc3_path.write_text(
        "\n".join(
            [
                "~V|FIEBDC-3/2020|",
                "~C|CAP#| |Capitulo general|0|20260323|CAP|",
                "~C|ITM1#CAP|m2|Muro bloque hueco|25.50|20260323|PART|",
                "~T|ITM1#|Muro de bloque con acabado base|",
                "~D|CAP#|ITM1\\1\\1|",
            ]
        ),
        encoding="latin-1",
    )

    parsed = parse_bc3(str(bc3_path))

    assert parsed["item_count"] == 1
    assert parsed["chapter_count"] == 1
    assert parsed["items"][0]["code"] == "ITM1"
    assert parsed["items"][0]["long_text"] == "Muro de bloque con acabado base"
    assert parsed.get("decomposition_parent_candidates", {}).get("ITM1") == ["CAP"]
