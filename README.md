# MailGuard OSS

**Telegram-Powered OTP & Email Automation Server**

A self-hosted OTP (One-Time Password) and email automation server with a Telegram bot admin interface. Deploy once, then call the REST API to add email OTP verification to any application.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Railway](https://img.shields.io/badge/Deploy-Railway-purple.svg)](https://railway.app)

---

## Features

- **🔐 OTP Verification** - Secure one-time password generation and verification
- **📧 Email Automation** - Send OTPs via SMTP with multiple provider support
- **🤖 Telegram Admin Bot** - Full administration through Telegram commands
- **🔑 API Key Management** - Generate and manage API keys for multiple projects
- **⚡ Rate Limiting** - Multi-tier rate limiting with Redis sliding windows
- **🔒 Security Hardened** - AES-256-GCM encryption, bcrypt hashing, JWT tokens
- **🆓 100% Free Tier** - Deploy on Railway + Supabase + Upstash for free

---

## Quick Start (3 Steps)

### Step 1: Set Up Database

Go to [supabase.com](https://supabase.com) and create a new project. Then run these SQL migrations in the SQL Editor:

```sql
-- Run migrations 001-006 in order
-- Files: db/migrations/001_create_sender_emails.sql through 006_create_bot_sessions.sql
```

### Step 2: Set Up Redis

Go to [upstash.com](https://upstash.com), create a free Redis database, and copy the connection URL.

### Step 3: Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/mailguard)

Or manually:

```bash
# Clone the repository
git clone https://github.com/yourusername/mailguard-oss.git
cd mailguard-oss

# Set environment variables in Railway
railway variables set SUPABASE_URL=your_url
railway variables set SUPABASE_SERVICE_ROLE_KEY=your_key
# ... etc

# Deploy
railway up
```

---

## Infrastructure Setup

### Required Services

| Service | Free Tier | Purpose |
|---------|-----------|---------|
| [Supabase](https://supabase.com) | 500MB DB | PostgreSQL database |
| [Upstash](https://upstash.com) | 500MB, 10K req/day | Redis for rate limiting & queues |
| [Railway](https://railway.app) | $5 credit/month | Hosting (3 lightweight services) |

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# Required
TELEGRAM_BOT_TOKEN=        # From @BotFather
TELEGRAM_ADMIN_UID=        # Your Telegram user ID (from @userinfobot)
SUPABASE_URL=              # From Supabase Settings > API
SUPABASE_SERVICE_ROLE_KEY= # From Supabase Settings > API (NOT anon key!)
REDIS_URL=                 # From Upstash (rediss://...)

# Generate these:
ENCRYPTION_KEY=            # python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=                # python -c "import secrets; print(secrets.token_hex(64))"
```

---

## API Reference

### Send OTP

```http
POST /api/v1/otp/send
Authorization: Bearer mg_live_your_api_key
Content-Type: application/json

{
  "email": "user@example.com",
  "purpose": "registration"
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "sent",
  "expires_in": 600,
  "masked_email": "u***@example.com"
}
```

### Verify OTP

```http
POST /api/v1/otp/verify
Authorization: Bearer mg_live_your_api_key
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456"
}
```

**Response:**
```json
{
  "verified": true,
  "token": "eyJ...",
  "expires_at": "2026-03-14T12:10:00Z"
}
```

---

## Code Examples

### Python

```python
import requests

BASE = 'https://your-api.up.railway.app'
HEADERS = {'Authorization': 'Bearer mg_live_your_key'}

# Send OTP
response = requests.post(
    f'{BASE}/api/v1/otp/send',
    headers=HEADERS,
    json={'email': user_email, 'purpose': 'registration'}
)

# Verify OTP
response = requests.post(
    f'{BASE}/api/v1/otp/verify',
    headers=HEADERS,
    json={'email': user_email, 'code': submitted_code}
)

if response.json()['verified']:
    # OTP verified - proceed with registration/login
    pass
```

### Node.js

```javascript
const BASE = 'https://your-api.up.railway.app';
const HEADERS = {
  'Authorization': 'Bearer mg_live_your_key',
  'Content-Type': 'application/json'
};

// Send OTP
const sendRes = await fetch(`${BASE}/api/v1/otp/send`, {
  method: 'POST',
  headers: HEADERS,
  body: JSON.stringify({ email: userEmail, purpose: 'registration' })
});

// Verify OTP
const verifyRes = await fetch(`${BASE}/api/v1/otp/verify`, {
  method: 'POST',
  headers: HEADERS,
  body: JSON.stringify({ email: userEmail, code: submittedCode })
});

const { verified } = await verifyRes.json();
```

---

## Telegram Bot Commands

### Sender Management
| Command | Description |
|---------|-------------|
| `/addemail` | Add a new sender email (interactive wizard) |
| `/senders` | List all sender emails |
| `/testsender <id>` | Test SMTP connection |
| `/removesender <id>` | Remove a sender |
| `/assignsender <project> <sender>` | Assign sender to project |

### Project Management
| Command | Description |
|---------|-------------|
| `/newproject` | Create a new project (interactive wizard) |
| `/projects` | List all projects |

### API Key Management
| Command | Description |
|---------|-------------|
| `/genkey <project> [label] [--test]` | Generate API key |
| `/keys <project>` | List API keys |
| `/revokekey <key_id>` | Revoke an API key |
| `/testkey <key> <email>` | Test an API key |

### Monitoring
| Command | Description |
|---------|-------------|
| `/logs [project] [--failed] [--today]` | View email logs |
| `/stats` | View statistics |

---

## Security Features

- **AES-256-GCM Encryption** - SMTP passwords encrypted at rest
- **bcrypt OTP Hashing** - Cost 10, constant-time comparison
- **HMAC Email Hashing** - Email addresses never stored in plaintext
- **SHA-256 API Key Hashing** - API keys hashed, never stored
- **JWT with JTI** - 10-minute expiry, single-use tokens
- **Rate Limiting** - 5 tiers of protection
- **Admin Gate** - Only authorized Telegram user can access bot

---

## Project Structure

```
mailguard/
├── apps/
│   ├── api/          # FastAPI REST API
│   ├── worker/       # ARQ async worker
│   └── bot/          # Telegram bot
├── core/
│   ├── config.py     # Pydantic settings
│   ├── crypto.py     # AES-256-GCM encryption
│   ├── db.py         # Supabase client
│   ├── otp.py        # OTP generation/verification
│   └── redis_client.py  # Redis & rate limiting
├── db/
│   └── migrations/   # SQL migrations (001-006)
├── tests/            # pytest tests
├── docker-compose.yml
├── railway.toml
└── requirements.txt
```

---

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations in Supabase SQL Editor

# Start services locally
docker-compose up

# Or run individually:
uvicorn apps.api.main:app --reload
python -m apps.worker.main
python -m apps.bot.main

# Run tests
pytest tests/ -v

# Lint
ruff check .
mypy apps/ core/
```

---

## Why Python?

The original TypeScript implementation suffered from frequent compilation errors during Railway builds. Python eliminates the build step entirely—no `tsc`, no `dist/` folder, no `tsconfig.json`. The server runs directly, eliminating an entire class of deployment failures.

| TypeScript (old) | Python (new) |
|-----------------|--------------|
| Fastify | FastAPI |
| grammY | python-telegram-bot |
| BullMQ | ARQ |
| Zod | Pydantic v2 |
| Nodemailer | aiosmtplib |
| Multi-stage Dockerfile | Single-stage Dockerfile |

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

---

## Support

- 📖 [Documentation](./docs/)
- 🐛 [Issues](https://github.com/yourusername/mailguard-oss/issues)
- 💬 [Discussions](https://github.com/yourusername/mailguard-oss/discussions)

---

**MailGuard OSS** • Railway + Supabase + Upstash • Python Edition • MIT License