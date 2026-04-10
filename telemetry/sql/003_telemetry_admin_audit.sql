-- Audit log for admin API mutations (Postman / automation).

CREATE TABLE IF NOT EXISTS telemetry_admin_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    method VARCHAR(16) NOT NULL,
    path VARCHAR(512) NOT NULL,
    actor_label VARCHAR(256),
    request_summary JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_telemetry_admin_audit_created_at
    ON telemetry_admin_audit (created_at DESC);
