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
        description="Root directory for job storage (inputs/outputs per UUID).",
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


def get_settings() -> Settings:
    return Settings()
