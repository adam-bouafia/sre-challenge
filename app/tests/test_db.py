from __future__ import annotations

import sqlite3

from ecorp import db


def _connect(db_path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def test_init_db_stores_a_hash_not_the_plaintext(tmp_path):
    connection = _connect(tmp_path / "x.db")
    db.init_db(connection, "admin", "secret123")

    row = connection.execute(
        "SELECT password FROM users WHERE username = ?", ("admin",)
    ).fetchone()

    assert row["password"] != "secret123"
    connection.close()


def test_init_db_is_idempotent_and_updates_password(tmp_path):
    connection = _connect(tmp_path / "x.db")

    db.init_db(connection, "admin", "first-password")
    db.init_db(connection, "admin", "second-password")

    rows = connection.execute(
        "SELECT * FROM users WHERE username = ?", ("admin",)
    ).fetchall()
    assert len(rows) == 1
    connection.close()


def test_table_exists(tmp_path):
    connection = _connect(tmp_path / "x.db")
    assert db.table_exists(connection, "users") is False

    db.init_db(connection, "admin", "secret123")

    assert db.table_exists(connection, "users") is True
    connection.close()
