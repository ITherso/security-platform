from pathlib import Path

import pytest

from security_platform import cli


def test_source_checkout_migration_resources_are_available():
    assert (cli._migration_root() / "migrations/env.py").is_file()


def test_installed_package_uses_prefix_share_migration_resources(tmp_path, monkeypatch):
    environment = tmp_path / "installed-environment"
    package = environment / "Lib/site-packages/security_platform/cli.py"
    resources = environment / "share/security-platform"
    (resources / "migrations/versions").mkdir(parents=True)
    (resources / "alembic.ini").write_text("[alembic]\n")
    monkeypatch.setattr(cli, "__file__", str(package))
    monkeypatch.setattr(cli.sys, "prefix", str(environment))
    assert cli._migration_root() == resources


def test_missing_migration_resources_fail_explicitly(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "__file__", str(tmp_path / "Lib/site-packages/security_platform/cli.py"))
    monkeypatch.setattr(cli.sys, "prefix", str(tmp_path))
    with pytest.raises(ValueError, match="Migration resources are unavailable"):
        cli._migration_root()
