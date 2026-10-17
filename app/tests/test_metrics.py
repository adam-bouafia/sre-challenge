from __future__ import annotations

from tests.conftest import ADMIN_USERNAME


def test_metrics_endpoint_exposes_login_counter(client):
    client.post("/login", data={"username": ADMIN_USERNAME, "password": "wrong"})

    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"ecorp_login_attempts_total" in response.data
