"""Isolated PostgreSQL draft journal; never a controller desired authority.

The explicit protected target must have been provisioned by the separate test
helper. This module has no bootstrap credential, URI argument or app-DB fallback.
Every read checks the complete bounded journal; append locks its singleton head.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from uuid import UUID, uuid4

import psycopg

from security_platform.connectors.hostbased_firewall.private_files import read_private_json
from security_platform.policy_contracts.fingerprints import adapter_fingerprint, canonical_bytes
from security_platform.policy_contracts.models import AdapterIdentity

from .models import (LabBinding, LabCheck, LabCommit, LabError, MAX_ENTRIES, MAX_JSON_BYTES,
                     MAX_STORE_BYTES, commit_revision, make_commit, make_head,
                     normalize_request, request_digest, validate_committed)

PROJECT = Path(__file__).resolve().parents[2]
WORKSPACE = PROJECT.parent
TARGET_MARKER = "security-platform-policy-revision-lab-target-v1"
_CONFIG_KEYS = {"schema_version", "owner", "workspace", "fixture_config", "cluster_dir",
                "host", "port", "database_name", "role", "connection_secret", "lab_id"}
_TABLES = {"stream", "entries"}


def _require(condition, code="lab_store_corrupt"):
    if not condition:
        raise LabError(code)


@dataclass(frozen=True, repr=False)
class _Target:
    database: str
    role: str
    port: int
    secret: str = field(repr=False)
    marker: dict = field(repr=False)


def _target(config_path):
    """Reject non-owned/local targets before opening any database connection."""
    try:
        config = read_private_json(config_path, maximum=16384)
        _require(set(config) == _CONFIG_KEYS, "invalid_lab_target")
        _require(type(config["schema_version"]) is int and config["schema_version"] == 1,
                 "invalid_lab_target")
        lab_id = UUID(config["lab_id"])
        _require(str(lab_id) == config["lab_id"], "invalid_lab_target")
        _require(config["owner"] == TARGET_MARKER and config["workspace"] == str(WORKSPACE)
                 and config["fixture_config"] == str(WORKSPACE / ".tooling" / "platform-test-env.json")
                 and config["host"] == "127.0.0.1"
                 and type(config["port"]) is int and 1024 <= config["port"] <= 65535
                 and config["database_name"] == "sp_policy_lab_" + lab_id.hex
                 and config["role"] == "spl_" + lab_id.hex
                 and isinstance(config["connection_secret"], str)
                 and re.fullmatch(r"[A-Za-z0-9_-]{43}", config["connection_secret"]), "invalid_lab_target")
        # Public provenance only: the provisioning helper verified this cluster.
        # The data writer never reads the app fixture's secret configuration.
        cluster = Path(config["cluster_dir"])
        _require(cluster.parent == WORKSPACE / ".tooling"
                 and re.fullmatch(r"test-pg-data-[a-f0-9]{32}", cluster.name), "invalid_lab_target")
        marker = {key: config[key] for key in ("owner", "lab_id", "database_name", "role", "cluster_dir")}
        return _Target(config["database_name"], config["role"], config["port"],
                       config["connection_secret"], marker)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise LabError("invalid_lab_target") from None


def _json(raw, model):
    _require(isinstance(raw, str) and len(raw.encode("utf-8")) <= MAX_JSON_BYTES)
    try:
        value = model.model_validate_json(raw)
        _require(canonical_bytes(value).decode("utf-8") == raw)
        return value
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise LabError("lab_store_corrupt") from None


def _entry_digest(lab_id, lineage, revision, digest, result, previous):
    return hashlib.sha256(canonical_bytes({"lab_id": lab_id, "lineage": lineage,
        "revision": revision, "request_digest": digest, "result": result,
        "previous_digest": previous})).hexdigest()


class ControllerStore:
    """One unassigned fixture stream in one explicitly marked lab database."""

    def __init__(self, config_path, binding, *, adapter):
        try:
            self.binding = LabBinding.model_validate(binding)
            _require(self.binding.kind == "controller_draft", "invalid_lab_binding")
            self.adapter = adapter
            self._adapter_fingerprint = adapter_fingerprint(AdapterIdentity.model_validate(adapter.identity))
        except (ValueError, TypeError, AttributeError):
            raise LabError("invalid_lab_binding") from None
        self._target = _target(config_path)

    @classmethod
    def init(cls, config_path, binding, *, adapter):
        store = cls(config_path, binding, adapter=adapter)
        with store._connection() as connection:
            store._area(connection, initialized=False)
            connection.execute("""CREATE TABLE lab.stream (
                singleton smallint PRIMARY KEY CHECK (singleton=1),
                schema_version smallint NOT NULL CHECK (schema_version=1),
                binding text NOT NULL CHECK (octet_length(binding)<=2048),
                lineage uuid NOT NULL,
                adapter_fingerprint text NOT NULL CHECK (adapter_fingerprint ~ '^sp-hbf-adapter-v1:sha256:[a-f0-9]{64}$'),
                head_revision bigint NOT NULL CHECK (head_revision BETWEEN 0 AND 128),
                head_fingerprint text,
                head_digest text CHECK (head_digest ~ '^[a-f0-9]{64}$'),
                CHECK ((head_revision=0 AND head_fingerprint IS NULL) OR
                       (head_revision>0 AND head_fingerprint ~ '^sp-hbf-bundle-v1:sha256:[a-f0-9]{64}$')),
                CHECK ((head_revision=0 AND head_digest IS NULL) OR (head_revision>0 AND head_digest IS NOT NULL))
            )""")
            connection.execute("""CREATE TABLE lab.entries (
                revision bigint PRIMARY KEY CHECK (revision BETWEEN 1 AND 128),
                operation_id uuid NOT NULL UNIQUE,
                request_json text NOT NULL CHECK (octet_length(request_json)<=3145728),
                result_json text NOT NULL CHECK (octet_length(result_json)<=16384),
                request_digest text NOT NULL CHECK (request_digest ~ '^sp-hbf-lab-request-v1:sha256:[a-f0-9]{64}$'),
                bundle_fingerprint text NOT NULL CHECK (bundle_fingerprint ~ '^sp-hbf-bundle-v1:sha256:[a-f0-9]{64}$'),
                previous_digest text CHECK (previous_digest ~ '^[a-f0-9]{64}$'),
                entry_digest text NOT NULL UNIQUE CHECK (entry_digest ~ '^[a-f0-9]{64}$')
            )""")
            connection.execute("INSERT INTO lab.stream VALUES (1,1,%s,%s,%s,0,NULL,NULL)",
                               (canonical_bytes(store.binding).decode("utf-8"), uuid4(), store._adapter_fingerprint))
        return store

    @classmethod
    def open(cls, config_path, binding, *, adapter):
        store = cls(config_path, binding, adapter=adapter)
        store.read()
        return store

    @contextmanager
    def _connection(self):
        target = self._target
        try:
            with psycopg.connect(host="127.0.0.1", port=target.port, dbname=target.database,
                    user=target.role, password=target.secret, connect_timeout=5,
                    options="-c statement_timeout=5000 -c lock_timeout=1500 -c search_path=pg_catalog,lab") as connection:
                yield connection
        except psycopg.Error as exc:
            code = "lab_store_busy" if exc.sqlstate in {"55P03", "57014"} else "lab_storage_unavailable"
            if exc.sqlstate in {"42P01", "42703", "23514", "23505", "3F000"}:
                code = "lab_store_corrupt"
            raise LabError(code) from None

    def _area(self, connection, *, initialized):
        target = self._target
        identity = connection.execute("SELECT current_database(),current_user,host(inet_server_addr()),inet_server_port()").fetchone()
        _require(identity == (target.database, target.role, "127.0.0.1", target.port), "invalid_lab_target")
        role = connection.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls "
                                  "FROM pg_roles WHERE rolname=current_user").fetchone()
        _require(role == (False,) * 6, "invalid_lab_target")
        _require(not connection.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)").fetchone(),
                 "invalid_lab_target")
        schemas = {row[0] for row in connection.execute("SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema'")}
        _require(schemas == {"public", "lab_identity", "lab"}, "invalid_lab_area")
        relations = connection.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                                       "WHERE n.nspname IN ('public','lab_identity','lab') AND c.relkind IN ('r','p','v','m','S','f')").fetchall()
        expected = {("lab_identity", "area")} | ({("lab", name) for name in _TABLES} if initialized else set())
        _require(set(relations) == expected, "invalid_lab_area")
        _require(not connection.execute("SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                                        "WHERE n.nspname IN ('public','lab_identity','lab') LIMIT 1").fetchone(), "invalid_lab_area")
        _require(not connection.execute("SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
                                        "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal "
                                        "AND n.nspname IN ('public','lab_identity','lab') LIMIT 1").fetchone(), "invalid_lab_area")
        _require(not connection.execute("SELECT 1 FROM pg_rewrite r JOIN pg_class c ON c.oid=r.ev_class "
                                        "JOIN pg_namespace n ON n.oid=c.relnamespace "
                                        "WHERE n.nspname IN ('public','lab_identity','lab') LIMIT 1").fetchone(), "invalid_lab_area")
        _require(not connection.execute("SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                                        "WHERE n.nspname IN ('public','lab_identity','lab') AND (c.relrowsecurity OR c.relforcerowsecurity) LIMIT 1").fetchone(),
                 "invalid_lab_area")
        marker = connection.execute("SELECT singleton,CASE WHEN octet_length(marker)<=4096 THEN marker END "
                                    "FROM lab_identity.area LIMIT 2").fetchall()
        _require(len(marker) == 1 and marker[0][0] == 1
                 and marker[0][1] == canonical_bytes(target.marker).decode("utf-8"), "invalid_lab_area")
        # The marker cannot be changed by the lab writer. Its schema/table are
        # owned by the independent fixture bootstrap, not this login.
        _require(not connection.execute("SELECT has_table_privilege(current_user,'lab_identity.area','INSERT,UPDATE,DELETE,TRUNCATE') "
                                        "OR has_schema_privilege(current_user,'lab_identity','CREATE')").fetchone()[0], "invalid_lab_area")
        _require(connection.execute("SELECT pg_get_userbyid(c.relowner),pg_get_userbyid(n.nspowner) FROM pg_class c "
                                    "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='lab_identity' AND c.relname='area'").fetchone()
                 == ("sp_test_bootstrap", "sp_test_bootstrap"), "invalid_lab_area")
        _require(not connection.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE') "
                                        "OR has_schema_privilege(current_user,'public','CREATE')").fetchone()[0], "invalid_lab_area")
        _require(connection.execute("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='lab'").fetchone()[0] == target.role,
                 "invalid_lab_area")
        if initialized:
            constraints = {(name, kind, tuple(columns)) for name, kind, columns in connection.execute(
                "SELECT c.conname,c.contype,ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(num,ord) "
                "JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.num ORDER BY k.ord) "
                "FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='lab'")}
            required = {("stream_pkey", "p", ("singleton",)), ("entries_pkey", "p", ("revision",)),
                        ("entries_operation_id_key", "u", ("operation_id",)),
                        ("entries_entry_digest_key", "u", ("entry_digest",))}
            _require(required <= constraints)

    def _read(self, connection, *, write=False):
        self._area(connection, initialized=True)
        lock = "FOR UPDATE" if write else "FOR SHARE"
        streams = connection.execute(
            "SELECT CASE WHEN octet_length(binding)<=2048 THEN binding END,lineage,"
            "CASE WHEN octet_length(adapter_fingerprint)<=256 THEN adapter_fingerprint END,head_revision,"
            "CASE WHEN octet_length(head_fingerprint)<=256 THEN head_fingerprint END,singleton,schema_version,"
            "CASE WHEN octet_length(head_digest)<=64 THEN head_digest END,"
            "octet_length(binding)<=2048 AND octet_length(adapter_fingerprint)<=256 "
            "AND coalesce(octet_length(head_fingerprint),0)<=256 AND coalesce(octet_length(head_digest),0)<=64 "
            "FROM lab.stream LIMIT 2 " + lock).fetchall()
        _require(len(streams) == 1)
        binding_raw, lineage, identity, revision, fingerprint, singleton, version, head_digest, metadata_ok = streams[0]
        _require(singleton == version == 1 and metadata_ok is True)
        _require(_json(binding_raw, LabBinding) == self.binding, "lab_binding_conflict")
        _require(identity == self._adapter_fingerprint, "lab_adapter_conflict")
        try:
            _require(identity == adapter_fingerprint(AdapterIdentity.model_validate(self.adapter.identity)), "lab_adapter_conflict")
        except (ValueError, TypeError, AttributeError):
            raise LabError("lab_adapter_conflict") from None
        _require(type(revision) is int and 0 <= revision <= MAX_ENTRIES)
        count, size, largest_request, largest_result, largest_digest, largest_fp, largest_prior, largest_entry = connection.execute(
            "SELECT count(*),coalesce(sum(octet_length(request_json)+octet_length(result_json)),0),"
            "coalesce(max(octet_length(request_json)),0),coalesce(max(octet_length(result_json)),0),"
            "coalesce(max(octet_length(request_digest)),0),coalesce(max(octet_length(bundle_fingerprint)),0),"
            "coalesce(max(octet_length(previous_digest)),0),coalesce(max(octet_length(entry_digest)),0) FROM lab.entries").fetchone()
        _require(count == revision and size <= MAX_STORE_BYTES and largest_request <= MAX_JSON_BYTES and largest_result <= 16384
                 and largest_digest <= 128 and largest_fp <= 128 and largest_prior <= 64 and largest_entry <= 64)
        history, prior_fingerprint, bundle, result, previous = {}, None, None, None, None
        from .models import AppendRequest
        for expected, row in enumerate(connection.execute("SELECT revision,operation_id,request_json,result_json,request_digest,bundle_fingerprint,previous_digest,entry_digest "
                                                         "FROM lab.entries ORDER BY revision"), 1):
            saved_revision, operation, request_raw, result_raw, digest, saved_fp, prior_digest, entry_digest = row
            _require(saved_revision == expected)
            request = _json(request_raw, AppendRequest)
            normalized = normalize_request(request, self.adapter)
            _require(canonical_bytes(normalized).decode("utf-8") == request_raw)
            result = validate_committed(request, _json(result_raw, LabCommit), self.adapter)
            _require(request.binding == self.binding and request.expected_lineage == str(lineage)
                     and request.expected_revision == expected - 1 and request.base_fingerprint == prior_fingerprint
                     and str(operation) == request.operation_id and result.lineage == str(lineage)
                     and commit_revision(result) == expected and digest == request_digest(request)
                     and digest == result.request_digest and saved_fp == result.bundle_fingerprint)
            _require(prior_digest == previous and entry_digest == _entry_digest(self._target.marker["lab_id"],
                     str(lineage), expected, digest, result.model_dump(mode="json"), previous))
            _require(request.operation_id not in history)
            history[request.operation_id] = (request_raw, result)
            prior_fingerprint, bundle = result.bundle_fingerprint, request.bundle
            previous = entry_digest
        _require(fingerprint == prior_fingerprint and head_digest == previous)
        return make_head(self.binding, str(lineage), revision, self.adapter, bundle, result), history, size, previous

    def read(self):
        with self._connection() as connection:
            return self._read(connection)[0]

    def check(self):
        head = self.read()
        return LabCheck(checked_entries=head.revision, head=head)

    def append(self, value):
        request = normalize_request(value, self.adapter)
        _require(request.binding == self.binding, "lab_binding_conflict")
        encoded = canonical_bytes(request).decode("utf-8")
        _require(len(encoded.encode("utf-8")) <= MAX_JSON_BYTES, "lab_capacity_exceeded")
        with self._connection() as connection:
            head, history, size, previous = self._read(connection, write=True)
            if request.operation_id in history:
                old_request, result = history[request.operation_id]
                _require(old_request == encoded, "lab_operation_conflict")
                return result
            _require(request.expected_lineage == head.lineage and request.expected_revision == head.revision
                     and request.base_fingerprint == head.bundle_fingerprint, "lab_cas_conflict")
            _require(head.revision < MAX_ENTRIES, "lab_capacity_exceeded")
            timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
            result = make_commit(request, head.lineage, head.revision + 1, timestamp)
            result_raw = canonical_bytes(result).decode("utf-8")
            _require(size + len(encoded.encode("utf-8")) + len(result_raw.encode("utf-8")) <= MAX_STORE_BYTES,
                     "lab_capacity_exceeded")
            entry_digest = _entry_digest(self._target.marker["lab_id"], head.lineage, commit_revision(result),
                                         result.request_digest, result.model_dump(mode="json"), previous)
            inserted = connection.execute("INSERT INTO lab.entries VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                                          "RETURNING request_json,result_json,entry_digest",
                               (commit_revision(result), UUID(request.operation_id), encoded, result_raw,
                                result.request_digest, result.bundle_fingerprint, previous, entry_digest)).fetchall()
            _require(inserted == [(encoded, result_raw, entry_digest)])
            updated = connection.execute("UPDATE lab.stream SET head_revision=%s,head_fingerprint=%s,head_digest=%s WHERE singleton=1 "
                                         "RETURNING head_revision,head_fingerprint,head_digest",
                               (commit_revision(result), result.bundle_fingerprint, entry_digest)).fetchall()
            _require(updated == [(commit_revision(result), result.bundle_fingerprint, entry_digest)])
            persisted = self._read(connection)[0]
            _require(persisted.revision == commit_revision(result) and persisted.last_commit == result)
        return result

    def close(self):
        pass  # Connections are bounded to each explicit operation; no worker.

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
