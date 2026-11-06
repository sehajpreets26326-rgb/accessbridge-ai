# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AccessBridge AI, please report it
responsibly by emailing the maintainers rather than opening a public issue.

## Secrets Management

- Never commit `.env` files or API keys. `.env.example` is the only
  environment file tracked in the repository.
- All secrets are loaded via environment variables (see `backend/app/config.py`).
- LLM API keys, Switch Trust credentials, and database URLs must be provided
  through environment variables only.
- Rotate any key that has been exposed immediately.

## Security Features

- Input validation and sanitisation on all API routes.
- Rate limiting on public endpoints.
- Secure error messages (no stack traces leaked to clients).
- Database transactions for data integrity.
- CORS configured to allow only trusted origins.
- Audit logging for agent actions.
- Idempotency keys to prevent duplicate processing.

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | ✅        |
