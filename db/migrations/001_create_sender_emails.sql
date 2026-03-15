-- Migration 001: Create sender_emails table
-- Stores SMTP sender email configurations with encrypted passwords

CREATE TABLE IF NOT EXISTS sender_emails (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_address    VARCHAR(255) NOT NULL UNIQUE,
  display_name     VARCHAR(100),
  provider         VARCHAR(50)  NOT NULL,
  smtp_host        VARCHAR(255) NOT NULL,
  smtp_port        SMALLINT     NOT NULL,
  app_password_enc TEXT         NOT NULL,  -- AES-256-GCM encrypted
  daily_limit      INTEGER      NOT NULL DEFAULT 500,
  emails_sent_today INTEGER     NOT NULL DEFAULT 0,
  is_verified      BOOLEAN      NOT NULL DEFAULT false,
  is_active        BOOLEAN      NOT NULL DEFAULT true,
  last_used_at     TIMESTAMPTZ,
  created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Index for quick lookups by email address
CREATE INDEX IF NOT EXISTS idx_sender_emails_email ON sender_emails(email_address);

-- Index for active sender lookup
CREATE INDEX IF NOT EXISTS idx_sender_emails_active ON sender_emails(is_active) WHERE is_active = true;

-- Comment
COMMENT ON TABLE sender_emails IS 'SMTP sender email configurations with encrypted passwords';
COMMENT ON COLUMN sender_emails.app_password_enc IS 'AES-256-GCM encrypted SMTP password';