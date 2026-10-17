from __future__ import annotations

import pytest

from ecorp import create_app, db
from ecorp.config import Config

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "elonmusk-is-a-humanoid"


def make_config(db_path: str, **overrides) -> Config:
    fields = {
        "secret_key": "test-secret-key",
        "database_path": db_path,
        "admin_username": ADMIN_USERNAME,
        "admin_password": ADMIN_PASSWORD,
        "session_cookie_secure": False,
        "log_level": "WARNING",
    }
    fields.update(overrides)
    return Config(**fields)


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "ecorp-test.db"
    application = create_app(make_config(str(db_path)))
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with application.app_context():
        db.init_db(db.get_db(), ADMIN_USERNAME, ADMIN_PASSWORD)

    yield application


@pytest.fixture
def client(app):
    return app.test_client()
