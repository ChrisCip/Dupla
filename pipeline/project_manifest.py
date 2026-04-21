"""
Carga de `project.yaml`: rutas, perfil de visión y fuentes opcionales por disciplina.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from budget.discipline_mapping import GENERAL, normalize_discipline_key


@dataclass
class VisionSourceSpec:
    """Un PDF (o directorio de imágenes) con disciplina explícita para visión."""

    pdf: Path | None = None
    images_dir: Path | None = None
    discipline: str = GENERAL
    use_pdf: bool = True


@dataclass
class ProjectManifest:
    project_name: str
    project_id: str
    dwg_path: Path
    outputs_dir: Path
    output_name: str = "dupla_budget_ready_full"
    pdf_path: Path | None = None
    images_dir: Path | None = None
    use_pdf: bool = True
    bc3_path: Path | None = None
    xlsx_training_path: Path | None = None
    bucket_name: str | None = None
    vision_profile: str | None = None
    vision_sources: list[VisionSourceSpec] = field(default_factory=list)
    pres_template_takeoffs: bool = False
    translation_views: tuple[str, ...] = ("2d",)
    translation_timeout_seconds: int = 3600
    poll_interval_seconds: int = 10
    max_property_wait_seconds: int = 3600
    failed_manifest_grace_polls: int = 3
    failed_manifest_grace_sleep_seconds: int = 20
    auto_unique_object_name: bool = True
    upload_object_name: str | None = None


def _resolve_path(base_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


def load_project_manifest(yaml_path: str | Path) -> ProjectManifest:
    path = Path(yaml_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Project manifest not found: {path}")
    base_dir = path.parent
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    paths = raw.get("paths") or {}
    vision_block = raw.get("vision") or {}

    vision_sources: list[VisionSourceSpec] = []
    for item in vision_block.get("sources") or []:
        disc = normalize_discipline_key(str(item.get("discipline", GENERAL)))
        pdf = _resolve_path(base_dir, item.get("pdf"))
        img = _resolve_path(base_dir, item.get("images_dir"))
        use_pdf = bool(item.get("use_pdf", True))
        vision_sources.append(
            VisionSourceSpec(pdf=pdf, images_dir=img, discipline=disc, use_pdf=use_pdf)
        )

    pdf_path = _resolve_path(base_dir, paths.get("pdf") or paths.get("pdf_path"))
    images_dir = _resolve_path(base_dir, paths.get("images_dir"))

    use_pdf = bool(raw.get("use_pdf", paths.get("use_pdf", True)))
    if vision_sources:
        use_pdf = vision_sources[0].use_pdf

    dwg_path = _resolve_path(base_dir, paths.get("dwg") or paths.get("dwg_path"))
    if not dwg_path:
        raise ValueError("project.yaml must set paths.dwg (or paths.dwg_path)")
    outputs_path = _resolve_path(base_dir, paths.get("outputs_dir") or "./output/run")
    if not outputs_path:
        raise ValueError("project.yaml must set paths.outputs_dir")

    tv = raw.get("translation_views") or ("2d",)
    if isinstance(tv, str):
        translation_views = (tv,)
    else:
        translation_views = tuple(str(x) for x in tv)

    return ProjectManifest(
        project_name=str(raw.get("project_name", "Unnamed")),
        project_id=str(raw.get("project_id", "project")),
        dwg_path=dwg_path,
        outputs_dir=outputs_path,
        output_name=str(raw.get("output_name", "dupla_budget_ready_full")),
        pdf_path=pdf_path,
        images_dir=images_dir,
        use_pdf=use_pdf,
        bc3_path=_resolve_path(base_dir, paths.get("bc3") or paths.get("bc3_path")),
        xlsx_training_path=_resolve_path(base_dir, paths.get("pres_training") or paths.get("xlsx_training")),
        bucket_name=raw.get("bucket_name"),
        vision_profile=vision_block.get("profile") or raw.get("vision_profile"),
        vision_sources=vision_sources,
        pres_template_takeoffs=bool(raw.get("pres_template_takeoffs", False)),
        translation_views=translation_views,
        translation_timeout_seconds=int(raw.get("translation_timeout_seconds", 3600)),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 10)),
        max_property_wait_seconds=int(raw.get("max_property_wait_seconds", 3600)),
        failed_manifest_grace_polls=int(raw.get("failed_manifest_grace_polls", 3)),
        failed_manifest_grace_sleep_seconds=int(raw.get("failed_manifest_grace_sleep_seconds", 20)),
        auto_unique_object_name=bool(raw.get("auto_unique_object_name", True)),
        upload_object_name=raw.get("upload_object_name"),
    )


def validate_manifest(m: ProjectManifest) -> list[str]:
    errors: list[str] = []
    if not m.dwg_path.exists():
        errors.append(f"DWG not found: {m.dwg_path}")
    if m.vision_sources:
        for i, src in enumerate(m.vision_sources):
            if src.use_pdf and src.pdf and not src.pdf.exists():
                errors.append(f"vision.sources[{i}].pdf not found: {src.pdf}")
            if not src.use_pdf and src.images_dir and not src.images_dir.is_dir():
                errors.append(f"vision.sources[{i}].images_dir not found: {src.images_dir}")
    else:
        if m.use_pdf and m.pdf_path and not m.pdf_path.exists():
            errors.append(f"PDF not found: {m.pdf_path}")
        if not m.use_pdf and m.images_dir and not m.images_dir.is_dir():
            errors.append(f"images_dir not found: {m.images_dir}")
    if m.bc3_path and not m.bc3_path.exists():
        errors.append(f"BC3 not found: {m.bc3_path}")
    if m.xlsx_training_path and not m.xlsx_training_path.exists():
        errors.append(f"PRES / training xlsx not found: {m.xlsx_training_path}")
    return errors
