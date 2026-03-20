from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GroupKind(str, Enum):
    TIRADA = "tirada"
    PLANO = "plano"
    FASE = "fase"


class ArchitectureItem(BaseModel):
    id: UUID
    descripcion: str = Field(..., min_length=1)
    capitulo: str | None = None
    partida: str | None = None
    unidad: str | None = None
    cantidad: float | None = Field(default=None, ge=0)
    precio_unitario: float | None = Field(default=None, ge=0)
    subtotal: float | None = Field(default=None, ge=0)
    notas: str | None = None


class ArchitectureGroup(BaseModel):
    id: UUID
    kind: GroupKind
    title: str = Field(..., min_length=1)
    order: int = Field(..., ge=0)
    items: list[ArchitectureItem] = Field(default_factory=list)


class MaterialRow(BaseModel):
    id: UUID
    categoria: str | None = None
    descripcion: str = Field(..., min_length=1)
    unidad: str | None = None
    cantidad_estimada: float | None = Field(default=None, ge=0)
    desperdicio_porcentaje: float | None = Field(default=None, ge=0, le=100)
    cantidad_total: float | None = Field(default=None, ge=0)
    costo_estimado: float | None = Field(default=None, ge=0)
    proveedor_sugerido: str | None = None


class ArchitectureDocumentPayload(BaseModel):
    groups: list[ArchitectureGroup] = Field(default_factory=list)
    materiales: list[MaterialRow] = Field(default_factory=list)

    @field_validator("groups")
    @classmethod
    def sort_groups(cls, v: list[ArchitectureGroup]) -> list[ArchitectureGroup]:
        return sorted(v, key=lambda g: g.order)


class ArchitectureDataResponse(BaseModel):
    project_uuid: UUID
    document: ArchitectureDocumentPayload
    updated_at: str | None = None
