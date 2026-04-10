"""Request/response models for admin (Postman) APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CatalogEventCreate(BaseModel):
    canonical_name: str = Field(..., min_length=1, max_length=256)
    display_name: str | None = Field(None, max_length=512)
    description: str | None = None
    lifecycle_status: Literal["active", "deprecated", "retired"] = "active"
    aliases: list[str] = Field(default_factory=list)
    catalog_metadata: dict[str, Any] = Field(default_factory=dict)


class CatalogEventOut(BaseModel):
    id: UUID
    canonical_name: str
    display_name: str | None
    description: str | None
    lifecycle_status: str
    catalog_metadata: dict[str, Any]
    aliases: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CatalogEventListResponse(BaseModel):
    events: list[CatalogEventOut]
    total: int


class CatalogResolveRequest(BaseModel):
    system_id: str = Field(..., min_length=1)
    tenant: str = ""
    event_name: str = Field(..., min_length=1)


DEFAULT_DESTINATIONS: dict[str, Any] = {
    "braze": {"enabled": True, "mapper_version": "braze_track_v1"},
    "ga4": {"enabled": False, "mapper_version": "ga4_mp_v1"},
}


class SystemCatalogConfigCreate(BaseModel):
    system_id: str = Field(..., min_length=1, max_length=128)
    tenant: str = Field(default="", max_length=128)
    canonical_event_name: str = Field(..., min_length=1)
    enabled: bool = True
    destinations: dict[str, Any] | None = None


class SystemCatalogConfigPatch(BaseModel):
    enabled: bool | None = None
    destinations: dict[str, Any] | None = None


class SystemCatalogConfigOut(BaseModel):
    id: UUID
    system_id: str
    tenant: str
    event_id: UUID
    canonical_name: str
    enabled: bool
    destinations: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SystemCatalogConfigListResponse(BaseModel):
    configs: list[SystemCatalogConfigOut]
