"""Upstox authentication and session management."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential
from upstox_api.api import Session, Upstox

from config.settings import Settings
from .logging_utils import get_logger

logger = get_logger(__name__)


class UpstoxSessionManager:
    """Handles access token lifecycle and client retrieval."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Optional[Upstox] = None
        self._token_path = Path(self.settings.data_dir) / "token_state.json"
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._load_tokens()

    def _load_tokens(self) -> None:
        if self._token_path.exists():
            payload = json.loads(self._token_path.read_text())
            self._access_token = payload.get("access_token")
            self._refresh_token = payload.get("refresh_token")
            expiry = payload.get("expires_at")
            if expiry:
                self._token_expiry = datetime.fromisoformat(expiry)

    def _persist_tokens(self, data: dict) -> None:
        self._token_path.write_text(json.dumps(data, indent=2))

    def initialize_session(self, authorization_code: str) -> Upstox:
        """Exchange auth code for tokens."""

        session = Session(self.settings.upstox_api_key)
        session.set_redirect_uri(self.settings.upstox_redirect_uri)
        session.set_api_secret(self.settings.upstox_api_secret)
        session.set_code(authorization_code)
        response = session.retrieve_access_token()
        self._access_token = response["access_token"]
        self._refresh_token = response.get("refresh_token")
        expires_in = response.get("expires_in", 3600)
        self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
        self._persist_tokens(
            {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at": self._token_expiry.isoformat(),
            }
        )
        self.client = Upstox(self.settings.upstox_api_key, self.settings.upstox_api_secret)
        self.client.set_access_token(self._access_token)
        return self.client

    def _token_valid(self) -> bool:
        return bool(self._access_token and self._token_expiry and datetime.utcnow() < self._token_expiry)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=2, max=30),
    )
    def refresh_access_token(self) -> None:
        if not self._refresh_token:
            raise ValueError("Missing refresh token; please re-authenticate manually.")

        session = Session(self.settings.upstox_api_key)
        session.set_api_secret(self.settings.upstox_api_secret)
        session.set_redirect_uri(self.settings.upstox_redirect_uri)
        session.set_token(self._refresh_token)
        response = session.refresh_access_token()
        self._access_token = response["access_token"]
        self._refresh_token = response.get("refresh_token", self._refresh_token)
        expires_in = response.get("expires_in", 3600)
        self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
        self._persist_tokens(
            {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at": self._token_expiry.isoformat(),
            }
        )
        if self.client:
            self.client.set_access_token(self._access_token)
        logger.info("Access token refreshed successfully.")

    def get_client(self) -> Upstox:
        """Return authenticated Upstox client, refreshing tokens if required."""

        if self.client and self._token_valid():
            return self.client

        if not self.client and self._access_token:
            self.client = Upstox(self.settings.upstox_api_key, self.settings.upstox_api_secret)
            self.client.set_access_token(self._access_token)

        if not self._token_valid():
            logger.warning("Access token expired; refreshing.")
            self.refresh_access_token()

        if not self.client:
            raise RuntimeError("Client not initialized; call initialize_session with auth code.")

        return self.client

    def get_access_token(self) -> str:
        if not self._access_token:
            raise RuntimeError("Access token not available; authenticate first.")
        if not self._token_valid():
            self.refresh_access_token()
        return self._access_token


__all__ = ["UpstoxSessionManager"]
