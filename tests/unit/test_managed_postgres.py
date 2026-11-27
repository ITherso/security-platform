"""Fixture ownership and secret-output checks; no PostgreSQL process is started."""
import importlib.util
from pathlib import Path
import subprocess
from unittest.mock import Mock

import psycopg
import pytest

_spec = importlib.util.spec_from_file_location("managed_postgres", Path(__file__).parents[2] / "scripts/managed_postgres.py")
managed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(managed)


def config():
    cluster = managed.TOOLING / ("test-pg-data-" + "a" * 32)
    row = {"owner": managed.MARKER, "workspace": str(managed.WORKSPACE), "host": "127.0.0.1",
        "port": 55439, "database": managed.DATABASE, "migration_role": managed.OWNER,
        "runtime_role": managed.RUNTIME, "bin_dir": str(managed.BIN), "cluster_dir": str(cluster),
        "bootstrap_password_file": str(managed.PRIVATE / (cluster.name + ".password")), "ready": True}
    for purpose, role, alias in (("migration", managed.OWNER, "SP_MIGRATION_DATABASE_URL"),
                                 ("runtime", managed.RUNTIME, "SP_DATABASE_URL")):
        row[purpose + "_password"] = "a" * 43
        row[purpose + "_url"] = managed._url(role, "a" * 43, row["port"])
        row[alias] = row[purpose + "_url"]
    return row


@pytest.mark.parametrize("field,value", [
    ("owner", "foreign"), ("workspace", "C:/foreign"), ("host", "0.0.0.0"),
    ("port", True), ("port", 543), ("port", 65536), ("database", "production"),
    ("migration_role", "postgres"), ("runtime_role", "postgres"), ("bin_dir", "C:/foreign"),
    ("cluster_dir", "C:/production-data"), ("bootstrap_password_file", "C:/other-password"),
    ("migration_url", "postgresql+psycopg://other-server/production"),
    ("runtime_password", "invalid"), ("ready", "true"),
])
def test_foreign_fixture_metadata_rejected_before_native_control(field, value):
    row = config()
    row[field] = value
    with pytest.raises(managed.FixtureError):
        managed._validate_config(row)


def test_valid_fixture_paths_stay_in_tooling():
    row = config()
    assert managed._validate_config(row).parent == managed.TOOLING


def test_directory_acl_changes_cannot_target_arbitrary_paths(tmp_path):
    with pytest.raises(managed.FixtureError, match="limited to owned"):
        managed._protect_directory(tmp_path)


def test_pg_ctl_capture_does_not_wait_on_a_detached_child_pipe(monkeypatch):
    def native(arguments, **kwargs):
        assert "capture_output" not in kwargs
        assert kwargs["stdout"] != subprocess.PIPE
        kwargs["stdout"].write(b"server started\n")
        return subprocess.CompletedProcess(arguments, 0)
    monkeypatch.setattr(managed.subprocess, "run", native)
    assert managed._run(["pg_ctl", "status"]).stdout == "server started\n"


def test_stop_never_signals_an_unverified_listening_server(monkeypatch):
    monkeypatch.setattr(managed, "_read_config", config)
    monkeypatch.setattr(managed, "_run", lambda args: subprocess.CompletedProcess(args, 0))
    monkeypatch.setattr(managed, "_owned_server", Mock(side_effect=managed.FixtureError("foreign server")))
    control = Mock()
    monkeypatch.setattr(managed, "_checked", control)
    with pytest.raises(managed.FixtureError, match="foreign server"):
        managed.stop()
    control.assert_not_called()


def test_driver_exception_cannot_print_password_or_connection_url(monkeypatch, capsys):
    monkeypatch.setattr(managed, "status", Mock(side_effect=psycopg.OperationalError(
        "password=PRIVATE_SECRET postgresql://role:PRIVATE_SECRET@localhost/database")))
    assert managed.main(["status"]) == 1
    output = capsys.readouterr()
    assert "PRIVATE_SECRET" not in output.err and "postgresql://" not in output.err
    assert "OperationalError" in output.err


def test_runtime_table_rights_allow_retention_but_not_audit_edits():
    assert set(managed.TABLE_GRANTS["audit_events"]) == {"SELECT", "INSERT", "DELETE"}
    assert managed.TABLE_GRANTS["principals"] == ("SELECT",)
    assert managed.TABLE_GRANTS["memberships"] == ("SELECT",)
    assert "DELETE" not in managed.TABLE_GRANTS["devices"]


def test_runtime_event_rights_are_append_and_retention_only():
    # Rows are never edited; DELETE serves the per-device cap and `events prune`.
    assert set(managed.TABLE_GRANTS["endpoint_events"]) == {"SELECT", "INSERT", "DELETE"}
    # SELECT FOR UPDATE on the cursor needs UPDATE; a cursor is never deleted.
    assert set(managed.TABLE_GRANTS["device_event_cursors"]) == {"SELECT", "INSERT", "UPDATE"}
    assert len(managed.TABLE_GRANTS) == 11


def test_runtime_alert_rights_add_delete_for_retention_only():
    # Ingestion raises and updates alerts, tenant admins acknowledge and close
    # them (UPDATE also covers SELECT FOR UPDATE). DELETE serves `alerts prune`
    # (migration 0006, alert retention); there is still no TRUNCATE.
    assert set(managed.TABLE_GRANTS["alerts"]) == {"SELECT", "INSERT", "UPDATE", "DELETE"}


def test_reparse_fixture_path_is_rejected_without_following(tmp_path, monkeypatch):
    original = Path.lstat
    def redirected(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == tmp_path:
            from types import SimpleNamespace
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path, "lstat", redirected)
    with pytest.raises(managed.FixtureError, match="reparse"):
        managed.no_links(tmp_path)
