"""this is the app factory, links config/db/auth/metrics into the actual routes
added CSRFProtect
added limit login
added session cookie flags like httpOnly, samesite nd secure
added healthz and readyz endpoints for k8s
"""

from __future__ import annotations

import logging
import sys

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from pythonjsonlogger import jsonlogger

from . import db, metrics
from .auth import sanitize_for_log, verify_credentials
from .config import Config

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def create_app(config: Config | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    cfg = config or Config.from_env()
    database_path = cfg.database_path or f"{app.instance_path}/ecorp.db"

    app.config.update(
        SECRET_KEY=cfg.secret_key,
        DATABASE_PATH=database_path,
        ADMIN_USERNAME=cfg.admin_username,
        ADMIN_PASSWORD=cfg.admin_password,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cfg.session_cookie_secure,
    )

    _configure_logging(app, cfg.log_level)
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    metrics.init_metrics(app)
    _register_routes(app)

    return app


def _register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        return render_template("index.html", is_authenticated=_is_authenticated())

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("5 per minute", methods=["POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if verify_credentials(db.get_db(), username, password):
                session.clear()
                session["username"] = username
                metrics.record_login_attempt(app, "success")
                app.logger.info(
                    "login attempt",
                    extra={
                        "username": sanitize_for_log(username),
                        "outcome": "success",
                    },
                )
                return redirect(url_for("index"))

            metrics.record_login_attempt(app, "failure")
            app.logger.warning(
                "login attempt",
                extra={"username": sanitize_for_log(username), "outcome": "failure"},
            )
            flash("Invalid credentials", "error")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.route("/readyz")
    def readyz():
        try:
            connection = db.get_db()
            if not db.table_exists(connection, "users"):
                raise RuntimeError("users table is missing")
            connection.execute("SELECT 1").fetchone()
        except Exception as exc:  # noqa: BLE001 - any db failure here just means not ready yet
            app.logger.error("readiness check failed", extra={"error": str(exc)})
            return {"status": "unavailable"}, 503
        return {"status": "ready"}, 200


def _is_authenticated() -> bool:
    return "username" in session


def _configure_logging(app: Flask, log_level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    app.logger.handlers = [handler]
    app.logger.setLevel(log_level)
    app.logger.propagate = False
