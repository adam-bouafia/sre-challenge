from __future__ import annotations

from flask import Flask
from flask.sessions import SecureCookieSessionInterface

from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def _forge_session_cookie(secret_key: str, data: dict) -> str:
    """Mint a session cookie as an attacker who guessed/leaked `secret_key`."""
    throwaway = Flask(__name__)
    throwaway.secret_key = secret_key
    serializer = SecureCookieSessionInterface().get_signing_serializer(throwaway)
    return serializer.dumps(data)


def test_login_success_redirects_to_index(client):
    response = client.post(
        "/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 302
    assert response.headers["Location"] in ("/", "http://localhost/")


def test_login_failure_rerenders_form_with_message(client):
    response = client.post(
        "/login", data={"username": ADMIN_USERNAME, "password": "wrong"}
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data
    assert b"Sign in" in response.data


def test_login_unknown_user_rerenders_form(client):
    response = client.post(
        "/login", data={"username": "nobody", "password": "whatever"}
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_login_does_not_log_password(app, client, caplog):
    app.logger.addHandler(caplog.handler)
    caplog.set_level("INFO", logger=app.logger.name)

    client.post("/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    client.post("/login", data={"username": ADMIN_USERNAME, "password": "wrong"})

    assert ADMIN_PASSWORD not in caplog.text
    assert "wrong" not in caplog.text


def test_forged_session_cookie_with_wrong_key_is_rejected(client):
    cookie_value = _forge_session_cookie(
        "some-other-key-an-attacker-might-guess", {"username": ADMIN_USERNAME}
    )
    client.set_cookie("session", cookie_value)

    response = client.get("/")

    assert b"Logout" not in response.data
    assert b"Incident" not in response.data


def test_login_requires_csrf_token_when_enabled(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post(
        "/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 400


def test_login_is_rate_limited_after_repeated_attempts(app, client):
    for _ in range(5):
        response = client.post(
            "/login", data={"username": ADMIN_USERNAME, "password": "wrong"}
        )
        assert response.status_code == 200

    response = client.post(
        "/login", data={"username": ADMIN_USERNAME, "password": "wrong"}
    )
    assert response.status_code == 429


def test_logout_via_get_is_not_allowed(client):
    response = client.get("/logout")
    assert response.status_code == 405


def test_logout_clears_session(client):
    client.post("/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})

    response = client.post("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Incident" not in response.data


def test_session_cookie_flags_are_set(client):
    response = client.post(
        "/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    cookie_header = response.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie_header
    assert "SameSite=Lax" in cookie_header
