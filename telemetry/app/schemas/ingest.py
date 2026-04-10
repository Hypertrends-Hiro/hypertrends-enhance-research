"""Universal ingest payload (aligned with telemetry/.plan/api-plan.html)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetaPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    message_id: str = Field(..., description="UUIDv7 recommended; idempotency key.")
    occurred_at: datetime = Field(..., description="Business time when the event happened at source.")
    source_system: str = Field(..., description="Emitting app or service name.")
    source_channel: str | None = Field(
        default=None,
        description="frontend | backend | cron | worker | admin",
    )
    tenant: str | None = Field(default=None, description="Tenant / brand / org slug.")
    schema_version: str | None = Field(default="1.0.0", description="Envelope schema version.")
    trace_id: str | None = None
    idempotency_key: str | None = None


class UserAttributesPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    first_name: str | None = None
    last_name: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)


class UserPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    external_id: str | None = None
    anonymous_id: str | None = None
    email: str | None = None
    phone: str | None = None
    attributes: UserAttributesPayload | None = None


class SessionPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: str | None = None
    page_url: str | None = None
    route: str | None = None
    user_agent: str | None = None
    ip: str | None = None


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Catalog event name.")
    time: datetime = Field(..., description="Usually same as meta.occurred_at.")
    properties: dict[str, Any] = Field(default_factory=dict)


class PurchasePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    product_id: str | None = None
    currency: str | None = None
    price: float | None = None
    quantity: int | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class IngestPayload(BaseModel):
    """Full universal envelope. Only send sections you need; optional blocks may be omitted."""

    model_config = ConfigDict(extra="allow")

    meta: MetaPayload
    user: UserPayload | None = None
    session: SessionPayload | None = None
    event: EventPayload
    purchase: PurchasePayload = Field(default_factory=PurchasePayload)


class IngestResponse(BaseModel):
    status: str = Field(..., description="accepted | duplicate_ignored | accepted_not_forwarded")
    message_id: str
    duplicate: bool = False
    received_at: datetime
    note: str | None = None
    forwarding: dict[str, str] | None = Field(
        default=None,
        description="Per-destination outcome, e.g. braze=ok|skipped|error",
    )


class BatchIngestRequest(BaseModel):
    items: list[IngestPayload] = Field(..., min_length=1, max_length=100)


class BatchItemResult(BaseModel):
    index: int
    message_id: str
    status: str
    duplicate: bool = False
    note: str | None = None
    forwarding: dict[str, str] | None = None


class BatchIngestResponse(BaseModel):
    results: list[BatchItemResult]
    received_at: datetime


class CatalogEventEntry(BaseModel):
    name: str
    description: str | None = None
    owner: str | None = None


class CatalogResponse(BaseModel):
    schema_version: str = "1.0.0"
    events: list[CatalogEventEntry] = Field(default_factory=list)
    note: str | None = "Populate from event_catalog.json in a later phase."
