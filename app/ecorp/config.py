"""config from env vars now, not hardcoded. no more secret_key baked into the file"""


from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """error raised when config is missing or invalid."""


def _as_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    secret_key: str
    database_path: str | None
    admin_username: str
    admin_password: str | None
    session_cookie_secure: bool
    log_level: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Config:
        env = os.environ if env is None else env

        secret_key = env.get("SECRET_KEY")
        if not secret_key:
            raise ConfigError("SECRET_KEY must be set, refusing to start without it")

        return cls(
            secret_key=secret_key,
            database_path=env.get("DATABASE_PATH"),
            admin_username=env.get("ADMIN_USERNAME", "admin"),
            admin_password=env.get("ADMIN_PASSWORD"),
            session_cookie_secure=_as_bool(
                env.get("SESSION_COOKIE_SECURE"), default=True
            ),
            log_level=env.get("LOG_LEVEL", "INFO").upper(),
        )