-- Migration 003: Create api_keys table
-- Stores API key hashes for project authentication

CREATE TABLE IF NOT EXISTS api_keys (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  key_hash     TEXT NOT NULL UNIQUE,  -- SHA-256 hash, never store plaintext
  key_prefix   VARCHAR(20) NOT NULL,  -- mg_live_ or mg_test_ prefix for identification
  label        VARCHAR(100),
  is_sandbox   BOOLEAN NOT NULL DEFAULT false,
  is_active    BOOLEAN NOT NULL DEFAULT true,
  last_used_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for key hash lookups (primary authentication path)
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

-- Index for project's keys
CREATE INDEX IF NOT EXISTS idx_api_keys_project ON api_keys(project_id);

-- Index for active keys
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;

-- Index for prefix lookups (debugging/identification)
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);

-- Comments
COMMENT ON TABLE api_keys IS 'API key hashes for project authentication';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the API key - plaintext never stored';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8-9 chars of key (mg_live_ or mg_test_) for identification';
COMMENT ON COLUMN api_keys.is_sandbox IS 'If true, key is for testing only - blocked in production';