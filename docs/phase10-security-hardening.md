# Phase 10: Security Hardening (Implemented)

## Objective
Implement the next pending phase by hardening authentication behavior.

## Implemented
- Upgraded `AuthService` to store and verify **hashed passwords** using PBKDF2-HMAC-SHA256.
- Added constant-time hash comparison for password verification.
- Added expiring token sessions (`token_ttl_seconds`).
- Added explicit logout and token revocation.
- Added `POST /auth/logout` route in HTTP transport.
- Added tests for logout invalidation and transport logout flow.

## Files
- `pharmacy_app/api.py`
- `pharmacy_app/http_server.py`
- `tests/test_service.py`
