-- Optional audit trail for each ingest decision (when table exists and app writes to it).

CREATE TABLE IF NOT EXISTS telemetry_ingest_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(128) NOT NULL,
    source_system VARCHAR(128) NOT NULL DEFAULT '',
    tenant VARCHAR(128) NOT NULL DEFAULT '',
    original_event_name VARCHAR(512) NOT NULL,
    canonical_name VARCHAR(256),
    event_id UUID REFERENCES catalog_events (id) ON DELETE SET NULL,
    decision VARCHAR(64) NOT NULL,
    forwarding JSONB NOT NULL DEFAULT '{}'::jsonb,
    note TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_ingest_audit_message_id
    ON telemetry_ingest_audit (message_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_ingest_audit_received_at
    ON telemetry_ingest_audit (received_at DESC);

COMMENT ON TABLE telemetry_ingest_audit IS 'One row per accepted ingest (not written for duplicate_ignored by default).';
