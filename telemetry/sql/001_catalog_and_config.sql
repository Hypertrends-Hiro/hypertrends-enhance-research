-- Telemetry: catalog (canonical events + aliases) and per-system routing config.
-- PostgreSQL 13+ (uses gen_random_uuid()).

CREATE TABLE IF NOT EXISTS catalog_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name VARCHAR(256) NOT NULL,
    display_name VARCHAR(512),
    description TEXT,
    lifecycle_status VARCHAR(32) NOT NULL DEFAULT 'active'
        CHECK (lifecycle_status IN ('active', 'deprecated', 'retired')),
    catalog_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT catalog_events_canonical_name_unique UNIQUE (canonical_name)
);

CREATE TABLE IF NOT EXISTS catalog_event_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES catalog_events (id) ON DELETE CASCADE,
    alias VARCHAR(512) NOT NULL,
    CONSTRAINT catalog_event_aliases_alias_unique UNIQUE (alias)
);

CREATE INDEX IF NOT EXISTS idx_catalog_event_aliases_event_id
    ON catalog_event_aliases (event_id);

CREATE INDEX IF NOT EXISTS idx_catalog_event_aliases_alias_lower
    ON catalog_event_aliases (lower(alias));

CREATE TABLE IF NOT EXISTS system_catalog_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    system_id VARCHAR(128) NOT NULL,
    tenant VARCHAR(128) NOT NULL DEFAULT '',
    event_id UUID NOT NULL REFERENCES catalog_events (id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT true,
    destinations JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT system_catalog_configs_unique_triple UNIQUE (system_id, tenant, event_id)
);

CREATE INDEX IF NOT EXISTS idx_system_catalog_configs_lookup
    ON system_catalog_configs (system_id, tenant, event_id);

COMMENT ON TABLE catalog_events IS 'Global canonical event dictionary (PascalCase names).';
COMMENT ON TABLE catalog_event_aliases IS 'Legacy / alternate strings that resolve to catalog_events.id.';
COMMENT ON TABLE system_catalog_configs IS 'Per system+tenant: enable event and destination toggles (Braze, GA4, …).';
