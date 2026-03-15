-- Migration 004: Create otp_records table
-- Stores OTP records with hashed emails and bcrypt-hashed OTP codes

CREATE TABLE IF NOT EXISTS otp_records (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  email_hash      TEXT NOT NULL,          -- HMAC-SHA256 hash, never store plaintext
  otp_hash        TEXT NOT NULL,          -- bcrypt cost 10
  purpose         VARCHAR(50),
  attempt_count   SMALLINT NOT NULL DEFAULT 0,
  is_verified     BOOLEAN NOT NULL DEFAULT false,
  is_invalidated  BOOLEAN NOT NULL DEFAULT false,
  expires_at      TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for email + project lookups (verification path)
CREATE INDEX IF NOT EXISTS idx_otp_records_email ON otp_records(email_hash, project_id);

-- Index for project's OTPs
CREATE INDEX IF NOT EXISTS idx_otp_records_project ON otp_records(project_id);

-- Index for active OTP lookup (verification query optimization)
CREATE INDEX IF NOT EXISTS idx_otp_records_active ON otp_records(project_id, email_hash, is_invalidated, expires_at) 
  WHERE is_invalidated = false;

-- Index for cleanup job (find expired OTPs)
CREATE INDEX IF NOT EXISTS idx_otp_records_expired ON otp_records(expires_at) WHERE is_invalidated = false;

-- Comments
COMMENT ON TABLE otp_records IS 'OTP records with hashed emails and bcrypt-hashed codes';
COMMENT ON COLUMN otp_records.email_hash IS 'HMAC-SHA256 hash of email - plaintext never stored';
COMMENT ON COLUMN otp_records.otp_hash IS 'bcrypt hash of OTP code (cost 10)';
COMMENT ON COLUMN otp_records.is_invalidated IS 'True after successful verify or explicit invalidation';