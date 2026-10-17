"""db schema, connection handling, and the init-db cli command.

no more plaintext password file (F2), no more relative db path (F5) - schema
and admin user get created at deploy time now via `flask init-db`
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
"""


def _resolve_db_path(app: Flask) -> Path:
    configured = app.config.get("DATABASE_PATH")
    if configured:
        return Path(configured)
    return Path(app.instance_path) / "ecorp.db"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = _resolve_db_path(current_app)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exception: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def init_db(
    connection: sqlite3.Connection, admin_username: str, admin_password: str
) -> None:
    """Create the schema and seed/update the admin user. Idempotent."""
    connection.executescript(SCHEMA)
    password_hash = generate_password_hash(admin_password)
    connection.execute(
        """
        INSERT INTO users (username, password) VALUES (:username, :password)
        ON CONFLICT(username) DO UPDATE SET password = excluded.password
        """,
        {"username": admin_username, "password": password_hash},
    )
    connection.commit()


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Create the schema and seed/update the admin user from env vars."""
    admin_password = current_app.config.get("ADMIN_PASSWORD")
    if not admin_password:
        raise click.ClickException(
            "ADMIN_PASSWORD must be set to initialize the database."
        )

    db_path = _resolve_db_path(current_app)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        init_db(connection, current_app.config["ADMIN_USERNAME"], admin_password)
    finally:
        connection.close()
    click.echo(f"Initialized the database at {db_path}")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
