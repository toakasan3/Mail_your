-- Migration 005: Create email_logs table
-- Stores logs of all sent emails for tracking and debugging

CREATE TABLE IF NOT EXISTS email_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  sender_email_id UUID NOT NULL REFERENCES sender_emails(id) ON DELETE SET NULL,
  email_hash      TEXT NOT NULL,          -- HMAC-SHA256 hash
  purpose         VARCHAR(50),
  status          VARCHAR(20) NOT NULL,   -- 'sent', 'failed', 'bounced'
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for project logs
CREATE INDEX IF NOT EXISTS idx_email_logs_project ON email_logs(project_id);

-- Index for sender logs
CREATE INDEX IF NOT EXISTS idx_email_logs_sender ON email_logs(sender_email_id);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_email_logs_created ON email_logs(created_at);

-- Index for failed email lookups
CREATE INDEX IF NOT EXISTS idx_email_logs_failed ON email_logs(status, created_at) WHERE status = 'failed';

-- Comments
COMMENT ON TABLE email_logs IS 'Email sending logs for tracking and debugging';
COMMENT ON COLUMN email_logs.status IS 'Delivery status: sent, failed, or bounced';