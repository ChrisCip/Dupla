from pathlib import Path

import yaml

from pipeline.project_manifest import load_project_manifest, validate_manifest


def test_load_project_manifest_minimal(tmp_path: Path) -> None:
    dwg = tmp_path / "a.dwg"
    dwg.write_bytes(b" ")
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    out = tmp_path / "out"
    yaml_path = tmp_path / "p.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "project_name": "T",
                "project_id": "t",
                "paths": {
                    "dwg": str(dwg.name),
                    "pdf": str(pdf.name),
                    "outputs_dir": str(out.name),
                },
                "vision": {"profile": "structural"},
            }
        ),
        encoding="utf-8",
    )
    m = load_project_manifest(yaml_path)
    assert m.project_id == "t"
    assert m.dwg_path.resolve() == dwg.resolve()
    assert validate_manifest(m) == []
