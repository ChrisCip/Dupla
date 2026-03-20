from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: Annotated[
        str,
        Field(
            default="postgresql+asyncpg://dupla:dupla@postgres:5432/dupla",
            description="Async SQLAlchemy URL",
        ),
    ]
    redis_url: Annotated[
        str,
        Field(default="redis://redis:6379/0", description="Redis URL for cache"),
    ]
    jwt_secret: Annotated[str, Field(default="demo-secret-change-in-production-min-32-chars!!")]
    jwt_algorithm: Annotated[str, Field(default="HS256")]
    access_token_expire_minutes: Annotated[int, Field(default=60, ge=1, le=60 * 24 * 7)]
    cors_origins: Annotated[str, Field(default="http://localhost:5173,http://127.0.0.1:5173")]
    cache_ttl_seconds: Annotated[int, Field(default=300, ge=1)]
    architecture_module_id: Annotated[int, Field(default=1, ge=1)]

    templates_dir: Annotated[str, Field(default="app/templates")]

    @field_validator("database_url")
    @classmethod
    def database_must_be_postgres_async(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use postgresql+asyncpg:// scheme")
        return v

    @field_validator("redis_url")
    @classmethod
    def redis_must_be_redis(cls, v: str) -> str:
        if not v.startswith("redis://"):
            raise ValueError("redis_url must start with redis://")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
