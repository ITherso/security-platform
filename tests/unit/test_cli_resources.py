from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from security_platform import cli
from security_platform.services.common import DEFAULT_LIMITS


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


# --- `security-platform sweep` without a database: the real sweep runs in tests/integration/test_stage3_alerts.py

RUNTIME_URL = "postgresql+psycopg://runtime@127.0.0.1:1/unused"
SWEEP_ENVIRONMENT = ("SP_DATABASE_URL", "SP_MIGRATION_DATABASE_URL", "SP_OPERATOR_ISSUER", "SP_OPERATOR_AUDIENCE",
                     "SP_JWKS_FILE", "SP_ALLOWED_HOSTS", "SP_SILENCE_ALERT_SECONDS", "SP_MAX_OPEN_ALERTS_PER_DEVICE")


class FakeDatabase:
    def __init__(self, url):
        self.url, self.closed = url, False

    def close(self):
        self.closed = True


@pytest.fixture
def sweep_double(monkeypatch):
    """cli.Database, validate_runtime_role and sweep_silent_agents replaced: no database is ever reached."""
    from security_platform import app
    from security_platform.services import sweep

    state = SimpleNamespace(databases=[], calls=[], role_error=None, result={
        "tenants": 3, "failed_tenants": 0, "devices_checked": 4, "alerts_opened": 1, "already_alerted": 2,
        "suppressed": 0, "devices_busy": 1})

    def database(url):
        state.databases.append(FakeDatabase(url))
        return state.databases[-1]

    def validate(database):
        if state.role_error is not None:
            raise ValueError(state.role_error)

    def sweep_silent_agents(database, *, silence_alert_seconds, limits):
        state.calls.append((database, silence_alert_seconds, limits))
        return dict(state.result)

    monkeypatch.setattr(cli, "Database", database)
    monkeypatch.setattr(app, "validate_runtime_role", validate)
    monkeypatch.setattr(sweep, "sweep_silent_agents", sweep_silent_agents)
    for name in SWEEP_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    return state


def test_sweep_needs_the_runtime_database_url_and_never_falls_back(sweep_double, monkeypatch, capsys):
    assert cli.main(["sweep"]) == 1
    assert capsys.readouterr().err.strip() == "SP_DATABASE_URL is required for the silence sweep"
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", RUNTIME_URL)
    assert cli.main(["sweep"]) == 1
    assert capsys.readouterr().err.strip() == "SP_DATABASE_URL is required for the silence sweep"
    monkeypatch.setenv("SP_DATABASE_URL", "sqlite:///sweep.db")
    assert cli.main(["sweep"]) == 1
    assert capsys.readouterr().err.strip() == "SP_DATABASE_URL is required for the silence sweep"
    assert (sweep_double.databases, sweep_double.calls) == ([], [])


def test_events_prune_keeps_its_own_message(monkeypatch, capsys):
    monkeypatch.delenv("SP_DATABASE_URL", raising=False)
    assert cli.main(["events", "prune"]) == 1
    assert capsys.readouterr().err.strip() == "SP_DATABASE_URL is required for event retention"


@pytest.mark.parametrize("name,value,message", [
    ("SP_SILENCE_ALERT_SECONDS", "299", "Invalid bounded platform setting"),
    ("SP_SILENCE_ALERT_SECONDS", "86401", "Invalid bounded platform setting"),
    ("SP_SILENCE_ALERT_SECONDS", "many", "Invalid integer setting: SP_SILENCE_ALERT_SECONDS"),
    ("SP_MAX_OPEN_ALERTS_PER_DEVICE", "9", "Invalid bounded platform setting"),
    ("SP_MAX_OPEN_ALERTS_PER_DEVICE", "many", "Invalid integer setting: SP_MAX_OPEN_ALERTS_PER_DEVICE"),
])
def test_sweep_refuses_an_invalid_setting_before_any_database(sweep_double, monkeypatch, capsys, name, value, message):
    monkeypatch.setenv("SP_DATABASE_URL", RUNTIME_URL)
    monkeypatch.setenv(name, value)
    assert cli.main(["sweep"]) == 1
    output = capsys.readouterr()
    assert (output.out, output.err.strip()) == ("", message)
    assert (sweep_double.databases, sweep_double.calls) == ([], [])


def test_sweep_passes_its_two_settings_and_prints_one_json_line(sweep_double, monkeypatch, capsys):
    # None of the HTTP server's operator settings (issuer, audience, JWKS file, hosts) is set.
    monkeypatch.setenv("SP_DATABASE_URL", RUNTIME_URL)
    assert cli.main(["sweep"]) == 0
    output = capsys.readouterr()
    assert (output.out, output.err) == (json.dumps(sweep_double.result) + "\n", "")
    [(database, seconds, limits)] = sweep_double.calls
    assert (database.url, database.closed, seconds, limits.max_open_alerts_per_device) == (RUNTIME_URL, True, 900, 500)
    assert replace(limits, max_open_alerts_per_device=DEFAULT_LIMITS.max_open_alerts_per_device) == DEFAULT_LIMITS
    monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", "3600")
    monkeypatch.setenv("SP_MAX_OPEN_ALERTS_PER_DEVICE", "25")
    assert cli.main(["sweep"]) == 0
    capsys.readouterr()
    assert (sweep_double.calls[-1][1], sweep_double.calls[-1][2].max_open_alerts_per_device) == (3600, 25)


def test_sweep_exits_1_on_a_failed_tenant_or_the_wrong_role(sweep_double, monkeypatch, capsys):
    monkeypatch.setenv("SP_DATABASE_URL", RUNTIME_URL)
    sweep_double.result["failed_tenants"] = 2
    assert cli.main(["sweep"]) == 1
    output = capsys.readouterr()
    # The counts are printed anyway: earlier chunks were committed.
    assert json.loads(output.out) == sweep_double.result
    assert output.err.strip() == ("sweep incomplete: 2 tenant(s) failed and were skipped; alerts already opened stay "
                                  "open and the next run retries the rest.")
    sweep_double.role_error = "The API requires a separate unprivileged runtime database role"
    calls = len(sweep_double.calls)
    assert cli.main(["sweep"]) == 1
    output = capsys.readouterr()
    assert (output.out, output.err.strip()) == ("", "sweep requires the separate unprivileged runtime database role")
    assert len(sweep_double.calls) == calls and all(database.closed for database in sweep_double.databases)


def test_a_database_error_before_any_chunk_records_no_success(sweep_double, monkeypatch, capsys):
    from security_platform.services import sweep

    def failing(database, *, silence_alert_seconds, limits):
        raise OperationalError("SELECT tenants", {}, Exception("connection refused"))

    monkeypatch.setattr(sweep, "sweep_silent_agents", failing)
    monkeypatch.setenv("SP_DATABASE_URL", RUNTIME_URL)
    assert cli.main(["sweep"]) == 1
    output = capsys.readouterr()
    assert (output.out, output.err.strip()) == ("", "Database operation failed; no success was recorded.")
    assert [database.closed for database in sweep_double.databases] == [True]


@pytest.mark.parametrize("arguments", [["--tenant-id", str(uuid4())], ["now"], ["--chunk-size", "5"]])
def test_sweep_takes_no_arguments(sweep_double, monkeypatch, capsys, arguments):
    monkeypatch.setenv("SP_DATABASE_URL", RUNTIME_URL)
    with pytest.raises(SystemExit) as raised:
        cli.main(["sweep", *arguments])
    assert raised.value.code == 2
    assert (sweep_double.databases, sweep_double.calls) == ([], [])
    capsys.readouterr()
