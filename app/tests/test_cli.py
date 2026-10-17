from __future__ import annotations

from ecorp import create_app
from tests.conftest import make_config


def test_init_db_command_seeds_admin_user(tmp_path):
    db_path = tmp_path / "cli.db"
    application = create_app(make_config(str(db_path)))
    runner = application.test_cli_runner()

    result = runner.invoke(args=["init-db"])

    assert result.exit_code == 0
    assert "Initialized the database" in result.output
    assert db_path.exists()


def test_init_db_command_requires_admin_password(tmp_path):
    db_path = tmp_path / "cli.db"
    application = create_app(make_config(str(db_path), admin_password=None))
    runner = application.test_cli_runner()

    result = runner.invoke(args=["init-db"])

    assert result.exit_code != 0
