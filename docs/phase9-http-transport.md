# Phase 9: HTTP Transport Layer (Implemented)

## Objective
Implement the next pending phase by binding API adapter methods to real HTTP routes.

## Implemented
- Added `pharmacy_app/http_server.py` with `PharmacyHTTPRequestHandler` and `build_server`.
- Exposed concrete routes:
  - `POST /auth/login`
  - `POST /medicines`
  - `POST /batches`
  - `POST /sales`
  - `GET /medicines/search?q=...`
  - `GET /reports/daily?day=YYYY-MM-DD`
- Added bearer-token header handling (`Authorization: Bearer <token>`).
- Added transport-level error mapping to HTTP-style status codes using `handle_api_error`.
- Added end-to-end HTTP transport test using an ephemeral local server.

## Files
- `pharmacy_app/http_server.py`
- `tests/test_service.py`
