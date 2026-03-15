# MailGuard OSS Security Policy

## Security Features

MailGuard OSS is designed with security as a primary concern. This document outlines our security practices and vulnerability disclosure policy.

### Encryption & Hashing

| Data | Protection |
|------|------------|
| SMTP Passwords | AES-256-GCM encryption with fresh IV per operation |
| OTP Codes | bcrypt hashing with cost factor 10 |
| Email Addresses | HMAC-SHA256 hashing (never stored in plaintext) |
| API Keys | SHA-256 hashing (plaintext never stored) |
| JWT Tokens | HS256 signing, 10-minute expiry, unique JTI claim |

### Key Management

- **ENCRYPTION_KEY**: Must be exactly 64 hex characters (32 bytes). Generate with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

- **JWT_SECRET**: Must be at least 64 characters. Generate with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(64))"
  ```

- Keys should be stored in Railway environment variables, never in code
- Rotate keys periodically (every 90 days recommended)

### Authentication

- **Supabase Service Role Key**: Used for server-side operations. NEVER expose this key client-side.
- **API Keys**: Two types:
  - `mg_live_*` - Production keys, stored hashed
  - `mg_test_*` - Sandbox keys, always return OTP "000000", blocked in production

### Rate Limiting

Five tiers of rate limiting protect against abuse:

| Tier | Limit | Window |
|------|-------|--------|
| Per email per project | 10 OTPs | 1 hour |
| Per API key | 1,000 requests | 1 hour |
| Per IP address | 100 requests | 15 minutes |
| Global per project | 10,000 OTPs | 1 day |
| SMTP per sender | 500 emails | 1 day |

### Anti-Enumeration

- Fixed 200ms minimum response time on OTP send
- Same response whether email exists or not
- No timing-based information leakage

### Telegram Bot Security

- **Admin Gate**: Only the configured `TELEGRAM_ADMIN_UID` can use the bot
- Silent rejection for unauthorized users
- Session data stored in database, not in memory

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x | ✅ Current release |

---

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow responsible disclosure:

### How to Report

1. **DO NOT** open a public GitHub issue
2. Email security concerns to: `security@example.com` (replace with actual email)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

| Time | Action |
|------|--------|
| 24 hours | Acknowledge receipt of report |
| 72 hours | Initial assessment and severity rating |
| 7 days | Detailed response with remediation plan |
| 30 days | Patch release for confirmed vulnerabilities |

### Disclosure Policy

- We follow responsible disclosure
- We ask that you give us 90 days to address the issue before public disclosure
- We will credit you in the security advisory (unless you prefer anonymity)

---

## Security Checklist

Before deploying to production, verify:

- [ ] All environment variables are set (no placeholders)
- [ ] `ENCRYPTION_KEY` is 64 hex characters
- [ ] `JWT_SECRET` is at least 64 characters
- [ ] Using `SUPABASE_SERVICE_ROLE_KEY` (NOT anon key)
- [ ] `TELEGRAM_ADMIN_UID` is set correctly
- [ ] `ENV=production` is set
- [ ] CORS is configured for your domains (not `["*"]`)
- [ ] All SQL migrations have been run
- [ ] API health check returns 200

---

## Security Headers

The API automatically adds security headers to all responses:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'
```

---

## Data Retention

- **OTP Records**: Automatically invalidated after expiry (typically 10 minutes)
- **Email Logs**: Stored indefinitely for auditing (configure retention policy as needed)
- **API Keys**: Active until explicitly revoked

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Internet / Clients                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Railway Load Balancer                     │
│                      (HTTPS Termination)                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Service                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Rate Limiting (Redis Sliding Window)                    ││
│  │ API Key Validation (SHA-256 Hash Lookup)                ││
│  │ Request Validation (Pydantic Schemas)                   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────┬───────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Supabase     │ │    Upstash      │ │ Telegram Bot    │
│   (PostgreSQL)  │ │    (Redis)      │ │   (Admin Only)  │
│                 │ │                 │ │                 │
│ - AES-256-GCM   │ │ - Rate Limits   │ │ - Sender Config │
│   Encrypted     │ │ - Task Queue    │ │ - Key Mgmt      │
│   Passwords     │ │ - Sessions      │ │ - Monitoring    │
│ - bcrypt OTPs   │ │                 │ │                 │
│ - HMAC Emails   │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Contact

For security concerns: `security@example.com`

For general questions: [GitHub Discussions](https://github.com/yourusername/mailguard-oss/discussions)

---

**Last Updated**: March 2026