from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_bc3_catalog_path() -> Path:
    """Bundled catalog: ``api/data/TGIU.bc3`` (package root = parent of ``app/``)."""
    api_dir = Path(__file__).resolve().parents[1]
    return api_dir / "data" / "TGIU.bc3"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    job_data_dir: Path = Field(
        default=Path(__file__).resolve().parents[1] / "data",
        description="Root directory for job storage (project_runs/, cache/).",
    )

    redis_url: str = Field(default="redis://127.0.0.1:6379/0")
    rq_queue_name: str = Field(default="dupla_jobs")

    api_prefix: str = Field(default="/api/v1")
    max_upload_mb: int = Field(default=200)

    # APS / Model Derivative (aligned with dupla_run_full_analysis_local defaults)
    aps_bucket_name: str | None = Field(default=None)
    upload_object_name: str | None = Field(default=None)
    auto_unique_object_name: bool = Field(default=True)
    translation_views: tuple[str, ...] = Field(default=("2d",))
    translation_timeout_seconds: int = Field(default=3600)
    poll_interval_seconds: int = Field(default=10)
    max_property_wait_seconds: int = Field(default=3600)
    failed_manifest_grace_polls: int = Field(default=3)
    failed_manifest_grace_sleep_seconds: int = Field(default=20)

    # Budget: static BC3 catalog (override with BC3_CATALOG_PATH). PRES.xlsx optional.
    bc3_catalog_path: Path = Field(default_factory=_default_bc3_catalog_path)
    pres_xlsx_path: Path | None = Field(default=None)

    # Project pipeline (GEBSA IV style)
    api_data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "data",
        description="Bundled BC3 / PRES under the api/ tree.",
    )
    artifact_cache_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "data" / "cache",
    )
    max_download_bytes: int = Field(
        default=200 * 1024 * 1024,
        description="Hard cap per file when downloading from URLs (bytes).",
    )
    download_timeout_seconds: float = Field(default=600.0)
    max_parallel_disciplines: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Run this many discipline pipelines in parallel (watch API rate limits).",
    )
    use_render_cache: bool = True


def get_settings() -> Settings:
    return Settings()
