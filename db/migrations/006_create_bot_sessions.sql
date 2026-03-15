-- Migration 006: Create bot_sessions table
-- Stores Telegram bot session data for multi-step wizards

CREATE TABLE IF NOT EXISTS bot_sessions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      VARCHAR(50) NOT NULL UNIQUE,  -- Telegram user ID
  session_data JSONB NOT NULL DEFAULT '{}',   -- Flexible session state
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_bot_sessions_user ON bot_sessions(user_id);

-- Comments
COMMENT ON TABLE bot_sessions IS 'Telegram bot session data for multi-step conversation wizards';
COMMENT ON COLUMN bot_sessions.session_data IS 'JSON object storing current wizard state';

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for bot_sessions
DROP TRIGGER IF EXISTS update_bot_sessions_updated_at ON bot_sessions;
CREATE TRIGGER update_bot_sessions_updated_at
    BEFORE UPDATE ON bot_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for sender_emails
DROP TRIGGER IF EXISTS update_sender_emails_updated_at ON sender_emails;
CREATE TRIGGER update_sender_emails_updated_at
    BEFORE UPDATE ON sender_emails
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for projects
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();