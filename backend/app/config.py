from functools import lru_cache
from typing import Annotated, Optional

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
            default="postgresql+asyncpg://dupla:dupla@127.0.0.1:5432/dupla",
            description=(
                "Async SQLAlchemy URL. Default targets localhost (run Postgres with exposed 5432). "
                "Docker Compose sets DATABASE_URL to host `postgres`."
            ),
        ),
    ]
    redis_url: Annotated[
        str,
        Field(
            default="redis://127.0.0.1:6379/0",
            description="Redis URL. Docker Compose sets REDIS_URL to host `redis`.",
        ),
    ]
    jwt_secret: Annotated[str, Field(default="demo-secret-change-in-production-min-32-chars!!")]
    jwt_algorithm: Annotated[str, Field(default="HS256")]
    access_token_expire_minutes: Annotated[int, Field(default=60, ge=1, le=60 * 24 * 7)]
    cors_origins: Annotated[str, Field(default="http://localhost:5173,http://127.0.0.1:5173")]
    cache_ttl_seconds: Annotated[int, Field(default=300, ge=1)]
    architecture_module_id: Annotated[int, Field(default=1, ge=1)]

    templates_dir: Annotated[str, Field(default="app/templates")]
    upload_root: Annotated[
        str,
        Field(
            default="var/uploads",
            description="Directorio raíz para archivos de proyecto (DWG/DXF, etc.).",
        ),
    ]
    project_file_max_mb: Annotated[
        int,
        Field(
            default=200,
            ge=1,
            le=2048,
            description="Tamaño máximo por archivo de proyecto (MB). CAD/BIM suele superar 50 MB.",
        ),
    ]
    openai_api_key: Annotated[
        Optional[str],
        Field(default=None, description="API key OpenAI: clasificación de archivos y Dupla Assistant (léela desde backend/.env)."),
    ] = None
    openai_model: Annotated[str, Field(default="gpt-4o-mini")] = "gpt-4o-mini"
    ai_assistant_context_ttl_seconds: Annotated[
        int,
        Field(
            default=604800,
            ge=60,
            le=60 * 60 * 24 * 90,
            description=(
                "TTL en Redis del historial del asistente IA por usuario (~7 días; cubre ~5 días laborales). "
                "Se renueva en cada mensaje (ventana deslizante)."
            ),
        ),
    ] = 604800
    ai_assistant_max_context_messages: Annotated[
        int,
        Field(
            default=40,
            ge=4,
            le=200,
            description="Máximo de mensajes user+assistant guardados en Redis (recorte por cola).",
        ),
    ] = 40

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
