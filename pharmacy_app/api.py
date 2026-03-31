from __future__ import annotations

from dataclasses import asdict
from datetime import date
import hashlib
import hmac
import secrets
import time
from uuid import uuid4

from pharmacy_app.models import PaymentMode, Role
from pharmacy_app.service import AuthorizationError, PharmacyService, ValidationError


class AuthError(PermissionError):
    """Raised for invalid credentials or token."""


class AuthService:
    """Auth service with hashed-password verification and expiring tokens."""

    def __init__(self, users: dict[str, dict], token_ttl_seconds: int = 3600) -> None:
        self._users = self._normalize_users(users)
        self._token_ttl_seconds = token_ttl_seconds
        self._tokens: dict[str, dict] = {}

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return digest.hex()

    @classmethod
    def _normalize_users(cls, users: dict[str, dict]) -> dict[str, dict]:
        normalized: dict[str, dict] = {}
        for username, raw in users.items():
            role = Role(raw["role"])
            if "password_hash" in raw and "salt" in raw:
                normalized[username] = {
                    "role": role,
                    "salt": raw["salt"],
                    "password_hash": raw["password_hash"],
                }
                continue

            if "password" not in raw:
                raise ValueError(f"Missing password/password_hash for user '{username}'")
            salt = raw.get("salt", secrets.token_hex(16))
            normalized[username] = {
                "role": role,
                "salt": salt,
                "password_hash": cls.hash_password(raw["password"], salt),
            }
        return normalized

    def login(self, username: str, password: str) -> str:
        account = self._users.get(username)
        if not account:
            raise AuthError("Invalid username or password")

        expected_hash = account["password_hash"]
        provided_hash = self.hash_password(password, account["salt"])
        if not hmac.compare_digest(provided_hash, expected_hash):
            raise AuthError("Invalid username or password")

        token = str(uuid4())
        self._tokens[token] = {
            "role": account["role"],
            "expires_at": time.time() + self._token_ttl_seconds,
        }
        return token

    def role_for_token(self, token: str) -> Role:
        token_data = self._tokens.get(token)
        if token_data is None:
            raise AuthError("Invalid or expired token")
        if time.time() > token_data["expires_at"]:
            self._tokens.pop(token, None)
            raise AuthError("Invalid or expired token")
        return token_data["role"]

    def logout(self, token: str) -> None:
        if token not in self._tokens:
            raise AuthError("Invalid or expired token")
        self._tokens.pop(token, None)


class PharmacyAPI:
    """Endpoint-style API adapter around PharmacyService."""

    def __init__(self, service: PharmacyService, auth: AuthService) -> None:
        self._service = service
        self._auth = auth

    def login(self, username: str, password: str) -> dict:
        token = self._auth.login(username=username, password=password)
        return {"token": token}

    def logout(self, token: str) -> dict:
        self._auth.logout(token)
        return {"status": "logged_out"}

    def add_medicine(self, token: str, payload: dict) -> dict:
        role = self._auth.role_for_token(token)
        medicine = self._service.add_medicine(role=role, **payload)
        return asdict(medicine)

    def add_batch(self, token: str, payload: dict) -> dict:
        role = self._auth.role_for_token(token)
        payload = payload.copy()
        payload["mfg_date"] = date.fromisoformat(payload["mfg_date"])
        payload["exp_date"] = date.fromisoformat(payload["exp_date"])
        batch = self._service.add_batch(role=role, **payload)
        raw = asdict(batch)
        raw["mfg_date"] = batch.mfg_date.isoformat()
        raw["exp_date"] = batch.exp_date.isoformat()
        return raw

    def search_medicine(self, token: str, query: str) -> dict:
        self._auth.role_for_token(token)
        return self._service.search_medicine(query)

    def create_sale(self, token: str, payload: dict) -> dict:
        role = self._auth.role_for_token(token)
        sale = self._service.create_sale(
            role=role,
            payment_mode=PaymentMode(payload["payment_mode"]),
            items=payload["items"],
            customer_name=payload.get("customer_name"),
        )
        return {
            "sale_id": sale.sale_id,
            "payment_mode": sale.payment_mode.value,
            "customer_name": sale.customer_name,
            "total_amount": sale.total_amount,
        }

    def daily_summary(self, token: str, day_iso: str) -> dict:
        self._auth.role_for_token(token)
        return self._service.daily_summary(date.fromisoformat(day_iso))


def handle_api_error(exc: Exception) -> dict:
    if isinstance(exc, AuthError):
        return {"error": str(exc), "status_code": 401}
    if isinstance(exc, AuthorizationError):
        return {"error": str(exc), "status_code": 403}
    if isinstance(exc, ValidationError):
        return {"error": str(exc), "status_code": 400}
    return {"error": str(exc), "status_code": 500}
