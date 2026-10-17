from __future__ import annotations

from ecorp import create_app
from tests.conftest import make_config


def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200


def test_readyz_ok_when_db_initialized(client):
    response = client.get("/readyz")
    assert response.status_code == 200


def test_readyz_fails_without_users_table(tmp_path):
    db_path = tmp_path / "empty.db"
    application = create_app(make_config(str(db_path)))
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    test_client = application.test_client()

    response = test_client.get("/readyz")

    assert response.status_code == 503
