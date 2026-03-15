-- Migration 002: Create projects table
-- Stores project configurations for OTP settings

-- Create enum for OTP format
CREATE TYPE otp_format AS ENUM ('text', 'html');

CREATE TABLE IF NOT EXISTS projects (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                VARCHAR(100) NOT NULL,
  slug                VARCHAR(100) NOT NULL UNIQUE,
  sender_email_id     UUID REFERENCES sender_emails(id) ON DELETE SET NULL,
  otp_length          SMALLINT     NOT NULL DEFAULT 6,
  otp_expiry_seconds  INTEGER      NOT NULL DEFAULT 600,
  otp_max_attempts    SMALLINT     NOT NULL DEFAULT 5,
  otp_subject_tmpl    TEXT,
  otp_body_tmpl       TEXT,
  otp_format          otp_format   NOT NULL DEFAULT 'text',
  rate_limit_per_hour INTEGER      NOT NULL DEFAULT 10,
  is_active           BOOLEAN      NOT NULL DEFAULT true,
  created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Index for slug lookups
CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);

-- Index for active projects
CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active) WHERE is_active = true;

-- Index for sender email relationship
CREATE INDEX IF NOT EXISTS idx_projects_sender ON projects(sender_email_id);

-- Comments
COMMENT ON TABLE projects IS 'Project configurations for OTP and email settings';
COMMENT ON COLUMN projects.slug IS 'URL-friendly project identifier';
COMMENT ON COLUMN projects.otp_subject_tmpl IS 'Jinja2 template for OTP email subject';
COMMENT ON COLUMN projects.otp_body_tmpl IS 'Jinja2 template for OTP email body';