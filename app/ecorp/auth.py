"""login check with parameterized query + a hash compare, not SELECT * + a python loop"""

from __future__ import annotations

import re
import sqlite3

from werkzeug.security import check_password_hash

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_for_log(value: str, max_length: int = 128) -> str:
    """strip control chars + cap length before this hits a log line.

    json logging already escapes this but a second layer cant hurt,
    especially against someone sticking a newline in the username field
    """
    cleaned = _CONTROL_CHARS.sub("", value)
    return cleaned[:max_length]


def find_user(connection: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, username, password FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def verify_credentials(
    connection: sqlite3.Connection, username: str, password: str
) -> bool:
    user = find_user(connection, username)
    if user is None:
        return False
    return check_password_hash(user["password"], password)
