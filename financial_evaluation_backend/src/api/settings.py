from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import List

from pydantic import BaseModel, Field, ValidationError


class _Settings(BaseModel):
    """Application settings loaded from environment variables.

    FRONTEND_ORIGIN controls CORS allow_origins and should match the frontend origin,
    e.g., http://localhost:3000 in local development. It can also be provided via
    REACT_APP_FRONTEND_URL for convenience in shared env files.
    """

    DEBUG: bool = Field(default=False, description="Enable debug mode.")
    SECRET_KEY: str = Field(default="change-me", description="Secret key for cryptographic uses.")
    FRONTEND_ORIGIN: str = Field(default="http://localhost:3000", description="Allowed CORS origin for the frontend.")
    MAX_UPLOAD_MB: int = Field(default=10, ge=1, le=100, description="Maximum upload size for files in megabytes.")
    ALLOWED_MIME_TYPES: List[str] = Field(
        default_factory=lambda: ["application/pdf", "image/png", "image/jpeg"],
        description="Whitelist of MIME types accepted for uploads.",
    )


def _get_env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_settings() -> _Settings:
    """Load and cache settings from environment variables."""
    raw_allowed = os.getenv("ALLOWED_MIME_TYPES", "")
    allowed_list = [m.strip() for m in raw_allowed.split(",") if m.strip()] if raw_allowed else None
    try:
        settings = _Settings(
            DEBUG=_get_env_bool("DEBUG", False),
            SECRET_KEY=os.getenv("SECRET_KEY", "change-me"),
            FRONTEND_ORIGIN=os.getenv("FRONTEND_ORIGIN", os.getenv("REACT_APP_FRONTEND_URL", "http://localhost:3000")),
            MAX_UPLOAD_MB=int(os.getenv("MAX_UPLOAD_MB", "10")),
            ALLOWED_MIME_TYPES=allowed_list if allowed_list is not None else _Settings.model_fields["ALLOWED_MIME_TYPES"].default_factory(),
        )
    except (ValueError, ValidationError) as exc:
        logging.getLogger("app").error("Invalid environment configuration: %s", exc)
        # Fail safe with defaults where possible
        settings = _Settings()  # type: ignore[call-arg]
    return settings
