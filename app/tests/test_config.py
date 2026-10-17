from __future__ import annotations

import pytest

from ecorp.config import Config, ConfigError


def test_from_env_requires_secret_key():
    with pytest.raises(ConfigError):
        Config.from_env({})


def test_from_env_reads_values():
    env = {
        "SECRET_KEY": "abc",
        "DATABASE_PATH": "/tmp/x.db",
        "ADMIN_USERNAME": "root",
        "SESSION_COOKIE_SECURE": "false",
        "LOG_LEVEL": "debug",
    }

    config = Config.from_env(env)

    assert config.secret_key == "abc"
    assert config.database_path == "/tmp/x.db"
    assert config.admin_username == "root"
    assert config.session_cookie_secure is False
    assert config.log_level == "DEBUG"


def test_from_env_defaults_session_cookie_secure_to_true():
    config = Config.from_env({"SECRET_KEY": "abc"})
    assert config.session_cookie_secure is True
