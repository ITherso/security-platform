"""Explicit private SQLite synthetic staging store. Never reads HBF runtime data."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from security_platform.connectors.hostbased_firewall.private_files import (
    ClientFileError, _check_ancestors, _install_private_windows_acl, _plain_path,
    read_private_json, validate_private_path, write_private_json,
)
from security_platform.policy_contracts.fingerprints import adapter_fingerprint, bundle_fingerprint, canonical_bytes
from security_platform.policy_contracts.models import AdapterIdentity

from .models import (AppendRequest, LabBinding, LabCheck, LabCommit, LabError, MAX_ENTRIES,
    MAX_JSON_BYTES, MAX_REVISION, MAX_STORE_BYTES, make_commit, make_head, normalize_request,
    request_digest, validate_committed)

MARKER_FILENAME = "policy-revision-lab.json"
DATABASE_FILENAME = "endpoint.sqlite3"
APPLICATION_ID = 0x53504C34
TABLES = {
    "lab_meta": "CREATE TABLE lab_meta (id INTEGER PRIMARY KEY CHECK(id=1), store_id TEXT NOT NULL, binding_json BLOB NOT NULL, lineage TEXT NOT NULL, adapter_fingerprint TEXT NOT NULL, head_revision INTEGER NOT NULL CHECK(head_revision>=0), head_fingerprint TEXT, head_digest TEXT)",
    "lab_entries": "CREATE TABLE lab_entries (revision INTEGER PRIMARY KEY CHECK(revision>=1), operation_id TEXT NOT NULL UNIQUE, request_json BLOB NOT NULL, request_digest TEXT NOT NULL, bundle_json BLOB NOT NULL, bundle_fingerprint TEXT NOT NULL, result_json BLOB NOT NULL, previous_digest TEXT, entry_digest TEXT NOT NULL UNIQUE)",
}


def _require(condition, code="lab_store_corrupt"):
    if not condition:
        raise LabError(code)


def _decode(raw):
    _require(type(raw) is bytes and len(raw) <= MAX_JSON_BYTES)
    def pairs(values):
        result = {}
        for key, value in values:
            _require(key not in result)
            result[key] = value
        return result
    def constant(value):
        raise LabError("lab_store_corrupt")
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        _require(type(result) is dict)
        return result
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise LabError("lab_store_corrupt") from exc


def _encoded(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    encoded = canonical_bytes(value)
    _require(len(encoded) <= MAX_JSON_BYTES, "lab_store_limit")
    return encoded


def _entry_digest(store_id, lineage, revision, request_hash, result, previous):
    return hashlib.sha256(canonical_bytes({"store_id": store_id, "lineage": lineage,
        "revision": revision, "request_digest": request_hash,
        "result": result.model_dump(mode="json"), "previous_digest": previous})).hexdigest()


class EndpointStore:
    """Every operation reopens and fully verifies the bounded immutable history."""
    def __init__(self, root, binding, adapter, marker):
        self.root, self.binding, self.adapter, self.marker = root, binding, adapter, marker

    @classmethod
    def init(cls, root, binding, adapter):
        try:
            binding = LabBinding.model_validate(binding)
            _require(binding.kind == "endpoint_staged", "lab_binding_mismatch")
            identity = AdapterIdentity.model_validate(adapter.identity)
            root = _plain_path(root)
            _check_ancestors(root)
            # Exclusive ownership: even an existing empty directory is not adopted.
            root.mkdir(mode=0o700)
            if os.name == "nt":
                _install_private_windows_acl(root)
            root = validate_private_path(root, directory=True)
            marker = {"schema_version": 1, "lab_kind": "endpoint_staged", "store_id": str(uuid4()),
                      "database": DATABASE_FILENAME, "binding": binding.model_dump(mode="json")}
            write_private_json(root / MARKER_FILENAME, marker)
            database = root / DATABASE_FILENAME
            descriptor = os.open(database, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            os.close(descriptor)
            if os.name == "nt":
                _install_private_windows_acl(database)
            store = cls(root, binding, adapter, marker)
            with store._connection(initializing=True) as connection:
                connection.execute("BEGIN IMMEDIATE")
                for ddl in TABLES.values():
                    connection.execute(ddl)
                connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                connection.execute("PRAGMA user_version=1")
                connection.execute("INSERT INTO lab_meta VALUES(1,?,?,?,?,0,NULL,NULL)",
                    (marker["store_id"], _encoded(binding), str(uuid4()), adapter_fingerprint(identity)))
                connection.commit()
            store.check()
            return store
        except FileExistsError as exc:
            raise LabError("lab_root_exists") from exc
        except LabError:
            raise
        except (OSError, ValueError, TypeError, AttributeError, sqlite3.Error) as exc:
            raise LabError("lab_store_unavailable") from exc

    @classmethod
    def open(cls, root, binding, adapter):
        try:
            binding = LabBinding.model_validate(binding)
            _require(binding.kind == "endpoint_staged", "lab_binding_mismatch")
            AdapterIdentity.model_validate(adapter.identity)
            root = validate_private_path(root, directory=True)
            marker = read_private_json(root / MARKER_FILENAME)
            expected_keys = {"schema_version", "lab_kind", "store_id", "database", "binding"}
            _require(set(marker) == expected_keys and type(marker["schema_version"]) is int
                and marker["schema_version"] == 1 and marker["lab_kind"] == "endpoint_staged"
                and marker["database"] == DATABASE_FILENAME)
            _require(str(UUID(marker["store_id"])) == marker["store_id"])
            _require(LabBinding.model_validate(marker["binding"]) == binding, "lab_binding_mismatch")
            store = cls(root, binding, adapter, marker)
            store.check()
            return store
        except LabError:
            raise
        except (OSError, ValueError, TypeError, AttributeError, sqlite3.Error) as exc:
            raise LabError("lab_store_unavailable") from exc

    def close(self):
        """Connections are operation-scoped; no persistent handles to close."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _paths(self):
        validate_private_path(self.root, directory=True)
        _require(read_private_json(self.root / MARKER_FILENAME) == self.marker)
        names = {MARKER_FILENAME, DATABASE_FILENAME, DATABASE_FILENAME + "-journal"}
        total = 0
        for path in self.root.iterdir():
            _require(path.name in names, "lab_root_unrecognized")
            try:
                path = validate_private_path(path)
                total += path.stat().st_size
            except FileNotFoundError:
                _require(path.name == DATABASE_FILENAME + "-journal")
        _require(total <= MAX_STORE_BYTES, "lab_store_limit")
        validate_private_path(self.root / DATABASE_FILENAME)

    @contextmanager
    def _connection(self, *, initializing=False):
        connection = None
        try:
            self._paths()
            # mode=rw cannot create a missing store. Journal remains within the
            # private directory; PERSIST avoids transient file races on reopen.
            uri = (self.root / DATABASE_FILENAME).as_uri() + "?mode=rw"
            connection = sqlite3.connect(uri, uri=True, timeout=3.0, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=3000")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA journal_mode=PERSIST")
            if not initializing:
                _require(connection.execute("PRAGMA application_id").fetchone()[0] == APPLICATION_ID)
                _require(connection.execute("PRAGMA user_version").fetchone()[0] == 1)
                actual = dict(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                _require(actual == TABLES)
                _require(not connection.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')").fetchone())
            yield connection
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc) or "busy" in str(exc):
                raise LabError("lab_store_busy") from exc
            raise LabError("lab_store_corrupt") from exc
        except (sqlite3.Error, ClientFileError, OSError, ValueError, TypeError) as exc:
            if isinstance(exc, LabError):
                raise
            raise LabError("lab_store_corrupt") from exc
        finally:
            if connection is not None:
                connection.close()

    def _validate(self, connection):
        _require(connection.execute("PRAGMA quick_check").fetchone()[0] == "ok")
        rows = connection.execute("SELECT * FROM lab_meta").fetchall()
        _require(len(rows) == 1 and rows[0]["id"] == 1)
        meta = rows[0]
        binding = LabBinding.model_validate(_decode(meta["binding_json"]))
        _require(_encoded(binding) == meta["binding_json"] and binding == self.binding)
        _require(meta["store_id"] == self.marker["store_id"])
        _require(meta["adapter_fingerprint"] == adapter_fingerprint(AdapterIdentity.model_validate(self.adapter.identity)),
                 "lab_adapter_mismatch")
        count = connection.execute("SELECT COUNT(*) FROM lab_entries").fetchone()[0]
        _require(type(meta["head_revision"]) is int and 0 <= count <= MAX_ENTRIES and count == meta["head_revision"])
        history = connection.execute("SELECT * FROM lab_entries ORDER BY revision").fetchall()
        previous, fingerprint, bundle, last, operations = None, None, None, None, {}
        for revision, entry in enumerate(history, 1):
            _require(entry["revision"] == revision)
            request = normalize_request(_decode(entry["request_json"]), self.adapter)
            _require(_encoded(request) == entry["request_json"] and request.binding == binding
                and request.expected_lineage == meta["lineage"] and request.expected_revision == revision - 1
                and request.base_fingerprint == fingerprint and request.operation_id == entry["operation_id"])
            _require(entry["request_digest"] == request_digest(request))
            bundle = request.bundle
            fingerprint = bundle_fingerprint(bundle)
            _require(entry["bundle_json"] == _encoded(bundle) and entry["bundle_fingerprint"] == fingerprint)
            last = validate_committed(request, _decode(entry["result_json"]), self.adapter)
            _require(_encoded(last) == entry["result_json"])
            expected = _entry_digest(meta["store_id"], meta["lineage"], revision, entry["request_digest"], last, previous)
            _require(entry["previous_digest"] == previous and entry["entry_digest"] == expected)
            previous = expected
            operations[request.operation_id] = (entry["request_json"], last)
        _require(meta["head_fingerprint"] == fingerprint and meta["head_digest"] == previous)
        return make_head(binding, meta["lineage"], count, self.adapter, bundle, last), operations, previous

    def read(self):
        with self._connection() as connection:
            connection.execute("BEGIN")
            head = self._validate(connection)[0]
            connection.commit()
            return head

    def check(self):
        head = self.read()
        return LabCheck(checked_entries=head.revision, head=head)

    def append(self, request):
        request = normalize_request(request, self.adapter)
        _require(request.binding == self.binding, "lab_binding_mismatch")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            head, operations, previous = self._validate(connection)
            encoded = _encoded(request)
            if request.operation_id in operations:
                prior, result = operations[request.operation_id]
                _require(prior == encoded, "lab_operation_conflict")
                connection.commit()
                return result
            _require(request.expected_lineage == head.lineage and request.expected_revision == head.revision
                and request.base_fingerprint == head.bundle_fingerprint, "lab_cas_conflict")
            _require(head.revision < MAX_REVISION, "lab_revision_overflow")
            _require(head.revision < MAX_ENTRIES, "lab_store_limit")
            revision = head.revision + 1
            result = make_commit(request, head.lineage, revision,
                datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"))
            digest = _entry_digest(self.marker["store_id"], head.lineage, revision, request_digest(request), result, previous)
            size = sum(len(value) for value in (encoded, _encoded(request.bundle), _encoded(result)))
            _require((self.root / DATABASE_FILENAME).stat().st_size + size * 3 < MAX_STORE_BYTES, "lab_store_limit")
            connection.execute("INSERT INTO lab_entries VALUES(?,?,?,?,?,?,?,?,?)",
                (revision, request.operation_id, encoded, request_digest(request), _encoded(request.bundle),
                 result.bundle_fingerprint, _encoded(result), previous, digest))
            connection.execute("UPDATE lab_meta SET head_revision=?,head_fingerprint=?,head_digest=? WHERE id=1",
                (revision, result.bundle_fingerprint, digest))
            connection.commit()
            return result
