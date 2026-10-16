"""this is the app factory, links config/db/auth/metrics into the actual routes"""

from __future__ import annotations

import logging
import sys

from flask import Flask, flash, redirect, render_template, request, session, url_for
from pythonjsonlogger import jsonlogger

from . import db, metrics
from .auth import sanitize_for_log, verify_credentials
from .config import Config


def create_app(config: Config | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    cfg = config or Config.from_env()
    database_path = cfg.database_path or f"{app.instance_path}/ecorp.db"

    app.config.update(
        SECRET_KEY=cfg.secret_key,
        DATABASE_PATH=database_path,
        ADMIN_USERNAME=cfg.admin_username,
        ADMIN_PASSWORD=cfg.admin_password,
    )

    _configure_logging(app, cfg.log_level)
    db.init_app(app)
    metrics.init_metrics(app)
    _register_routes(app)

    return app


def _register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        return render_template("index.html", is_authenticated=_is_authenticated())

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if verify_credentials(db.get_db(), username, password):
                session.clear()
                session["username"] = username
                metrics.record_login_attempt("success")
                app.logger.info(
                    "login attempt",
                    extra={"username": sanitize_for_log(username), "outcome": "success"},
                )
                return redirect(url_for("index"))

            metrics.record_login_attempt("failure")
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


def _is_authenticated() -> bool:
    return "username" in session


def _configure_logging(app: Flask, log_level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    app.logger.handlers = [handler]
    app.logger.setLevel(log_level)
    app.logger.propagate = False
