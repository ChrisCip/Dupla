"""Orchestrates a full project pipeline run: download → shared → per discipline."""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.services.project_run_store import ProjectRunRecord, ProjectRunStore
from app.services.project_pipeline.artifact_cache import ArtifactCache
from app.services.project_pipeline.download_service import download_batch
from core.output_structure import RunOutputDir
from pipeline.project_pipeline import ApsOptions, load_shared_resources, pdf_pages_cache_dir, process_discipline

logger = logging.getLogger("dupla.api.orchestrator")


def _orchestrate_impl(run_id: str, settings: Settings) -> None:
    store = ProjectRunStore(settings.job_data_dir)
    rec = store.get(run_id)
    if rec is None:
        logger.error("Unknown run_id: %s", run_id)
        return

    rec.status = "running"
    store.update(rec)
    log_path = store.run_root(run_id) / "dupla_debug.log"
    _attach_file_log(log_path)

    try:
        api_data = settings.api_data_dir
        if not list(api_data.glob("*.bc3")):
            raise FileNotFoundError(f"No .bc3 under {api_data}")
        shared = load_shared_resources(api_data)
    except Exception as exc:  # noqa: BLE001
        _fail(store, rec, str(exc))
        return

    order = [d for d in rec.discipline_order if d in {x.id for x in rec.inputs}]
    if not order:
        _fail(store, rec, "no disciplines in order")
        return

    dwg_name = "input.dwg"
    pdf_name = "input.pdf"
    in_root = store.inputs_root(run_id)
    dl_tasks: list[dict[str, Any]] = []
    for inp in rec.inputs:
        ddir = in_root / inp.id
        if inp.dwg_url and not rec.skip_aps:
            dl_tasks.append(
                {
                    "key": f"{inp.id}__dwg",
                    "url": inp.dwg_url,
                    "path": ddir / dwg_name,
                    "max_bytes": settings.max_download_bytes,
                    "timeout_seconds": settings.download_timeout_seconds,
                }
            )
        if inp.pdf_url:
            dl_tasks.append(
                {
                    "key": f"{inp.id}__pdf",
                    "url": inp.pdf_url,
                    "path": ddir / pdf_name,
                    "max_bytes": settings.max_download_bytes,
                    "timeout_seconds": settings.download_timeout_seconds,
                }
            )

    if dl_tasks:
        err_map = download_batch(dl_tasks, max_workers=min(8, len(dl_tasks) or 1))
        first_err = next((err_map[k] for k in err_map if err_map[k]), None)
        if first_err:
            _fail(store, rec, f"Download failed: {first_err}")
            return

    cache = ArtifactCache(settings.artifact_cache_dir)
    run_dir = RunOutputDir(store.workspace(run_id), rec.project_name, timestamp=rec.run_id)

    aps = ApsOptions(
        translation_views=settings.translation_views,
        translation_timeout_seconds=settings.translation_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
        max_property_wait_seconds=settings.max_property_wait_seconds,
        failed_manifest_grace_polls=settings.failed_manifest_grace_polls,
        failed_manifest_grace_sleep_seconds=settings.failed_manifest_grace_sleep_seconds,
        auto_unique_object_name=settings.auto_unique_object_name,
        upload_object_name=settings.upload_object_name,
        bucket_name=settings.aps_bucket_name,
    )

    _w = rec.max_discipline_workers
    if _w is None:
        _w = int(settings.max_parallel_disciplines)
    max_d = max(1, min(4, int(_w or 1)))
    def run_one(disc_id: str) -> tuple[str, dict[str, Any] | None, str | None]:
        inp = next((i for i in rec.inputs if i.id == disc_id), None)
        if inp is None:
            return disc_id, None, "missing input"
        dpath = in_root / disc_id
        pdf_p = dpath / pdf_name
        if not pdf_p.is_file():
            return disc_id, None, f"PDF not found for {disc_id}"
        files: dict[str, str] = {"pdf": str(pdf_p)}
        dwg_p = dpath / dwg_name
        if not rec.skip_aps and dwg_p.is_file():
            files["dwg"] = str(dwg_p)
        pages_override: Path | None = None
        if settings.use_render_cache and cache.materialize_render_to(pdf_p, run_dir.discipline_dir(disc_id) / "cached_pages"):
            pages_override = run_dir.discipline_dir(disc_id) / "cached_pages"
        else:
            pages_override = None
        try:
            res = process_discipline(
                disc_id,
                files,
                run_dir,
                shared,
                project_id=rec.project_id,
                project_name=rec.project_name,
                aps=aps,
                vision_max_workers=rec.max_vision_workers,
                pages_dir_override=pages_override,
            )
            if settings.use_render_cache:
                if pages_override is not None and pages_override.is_dir():
                    cache.publish_rendered_dir(pdf_p, pages_override)
                else:
                    rd = pdf_pages_cache_dir(run_dir.discipline_dir(disc_id), pdf_p)
                    if rd.is_dir():
                        cache.publish_rendered_dir(pdf_p, rd)
        except Exception as exc:  # noqa: BLE001
            return disc_id, None, str(exc)
        return disc_id, res, None

    disc_states: dict[str, Any] = {d: rec.disciplines.get(d, {"status": "pending"}) for d in order}
    if max_d == 1:
        for did in order:
            key, res, err = run_one(did)
            if err:
                disc_states[key] = {"status": "error", "error": err}
                rec.disciplines = disc_states
                store.update(rec)
                _fail(store, rec, f"discipline {key}: {err}")
                return
            disc_states[key] = res
            rec.disciplines = disc_states
            store.update(rec)
    else:
        with ThreadPoolExecutor(max_workers=max_d) as ex:
            fmap = {ex.submit(run_one, d): d for d in order}
            for fut in as_completed(fmap):
                key, res, err = fut.result()
                if err:
                    disc_states[key] = {"status": "error", "error": err}
                else:
                    disc_states[key] = res
                rec.disciplines = disc_states
                store.update(rec)
        if any(
            isinstance(disc_states.get(d), dict) and disc_states.get(d, {}).get("status") == "error"
            for d in order
        ):
            _fail(
                store,
                rec,
                "one or more disciplines failed: "
                + json.dumps(
                    {k: v for k, v in disc_states.items() if v.get("status") == "error"},
                    default=str,
                )[:2000],
            )
            return

    rec.status = "succeeded"
    rec.work_subdir = str(run_dir.root.relative_to(store.run_root(run_id)))
    rec.run_summary = {
        "project": rec.project_name,
        "output_dir": str(run_dir.root),
        "disciplines": disc_states,
    }
    (store.run_root(run_id) / "run_summary.json").write_text(
        json.dumps(rec.run_summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    if run_dir.run_summary.is_file():
        pass
    else:
        run_dir.run_summary.write_text(
            json.dumps(rec.run_summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
    store.update(rec)
    logger.info("Run %s succeeded", run_id)


def _fail(store: ProjectRunStore, rec: ProjectRunRecord, err: str) -> None:
    rec.status = "failed"
    rec.error = err
    store.update(rec)
    logger.error("Run %s failed: %s", rec.run_id, err)


def _attach_file_log(path: Path) -> None:
    try:
        fh = logging.FileHandler(str(path), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        root = logging.getLogger()
        root.addHandler(fh)
    except OSError as exc:
        logger.warning("Could not open debug log: %s", exc)


def execute_project_run(run_id: str) -> None:
    settings = get_settings()
    _orchestrate_impl(run_id, settings)
