"""Record/check a bounded Vite asset graph. Does not execute tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
ENTRY_JS = "assets/console.js"
LEGACY_ASSETS = ("index.html", ENTRY_JS, "assets/console.css")
MANIFEST = "build-manifest.json"
VITE_MANIFEST = "vite-manifest.json"
MAX_ASSET_FILES = 32
MAX_ASSET_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_VITE_MANIFEST_BYTES = 128 * 1024
MAX_GRAPH_EDGES = 128
CHUNK_NAME = re.compile(r"assets/[A-Za-z0-9_][A-Za-z0-9_-]{0,79}-[A-Za-z0-9_-]{8,16}\.(?:js|css)")
HEX = re.compile(r"[a-f0-9]{64}")


class BuildError(ValueError):
    pass


def _require(condition):
    if not condition:
        raise BuildError("console_assets_unavailable")


def _plain(path, *, directory=False):
    for candidate in (path, *path.parents):
        info = candidate.lstat()
        _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400)
    info = path.stat()
    _require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
    return path


def _read(path, maximum=MAX_ASSET_BYTES):
    _plain(path)
    with path.open("rb") as stream:
        value = stream.read(maximum + 1)
    _require(len(value) <= maximum)
    return value


def _safe_name(name):
    return (isinstance(name, str) and len(name) <= 128
            and (name in LEGACY_ASSETS or CHUNK_NAME.fullmatch(name) is not None))


def _rows(assets):
    return [{"path": name, "bytes": len(assets[name]), "sha256": hashlib.sha256(assets[name]).hexdigest()}
            for name in sorted(assets)]


def _digest(rows):
    encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dist_layout(*, staging=False):
    _plain(DIST, directory=True)
    allowed = {"index.html", "assets", MANIFEST} | ({VITE_MANIFEST} if staging else set())
    for path in DIST.iterdir():
        _require(path.name in allowed)
        _plain(path, directory=path.name == "assets")
    source = DIST / "assets"
    _plain(source, directory=True)
    assets = {"index.html": DIST / "index.html"}
    for path in source.iterdir():
        name = "assets/" + path.name
        _require(_safe_name(name))
        _plain(path)
        assets[name] = path
    # One old and one newly emitted build may coexist until exact stale cleanup.
    _require(len(assets) <= MAX_ASSET_FILES * (2 if staging else 1)
             and len({name.casefold() for name in assets}) == len(assets))
    _plain(assets["index.html"])
    return assets


def _json(raw):
    def unique(pairs):
        value = {}
        for key, child in pairs:
            _require(key not in value)
            value[key] = child
        return value
    def constant(_):
        raise BuildError("console_assets_unavailable")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as error:
        raise BuildError("console_assets_unavailable") from error


def _file_rows(rows, *, sorted_rows=True):
    _require(type(rows) is list and 3 <= len(rows) <= MAX_ASSET_FILES)
    names = []
    for row in rows:
        _require(type(row) is dict and set(row) == {"path", "bytes", "sha256"})
        name = row["path"]
        _require(_safe_name(name) and type(row["bytes"]) is int and 0 < row["bytes"] <= MAX_ASSET_BYTES
                 and isinstance(row["sha256"], str) and HEX.fullmatch(row["sha256"]) is not None)
        names.append(name)
    _require("index.html" in names and ENTRY_JS in names
             and len({name.casefold() for name in names}) == len(names)
             and sum(row["bytes"] for row in rows) <= MAX_TOTAL_BYTES)
    if sorted_rows:
        _require(names == sorted(names))
    return set(names)


def _names(value, allowed):
    _require(type(value) is list and len(value) <= MAX_ASSET_FILES
             and all(isinstance(name, str) and name in allowed for name in value)
             and value == sorted(set(value)))
    return value


def _closure(graph, *, dynamic=False):
    pending, seen = [ENTRY_JS], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        _require(name in graph)
        seen.add(name)
        seen.update(graph[name]["css"])
        pending.extend(graph[name]["imports"])
        if dynamic:
            pending.extend(graph[name]["dynamic_imports"])
    return seen | {"index.html"}


def _graph_fields(files, rows):
    js = {name for name in files if name.endswith(".js")}
    css = {name for name in files if name.endswith(".css")}
    _require(type(rows) is list and len(rows) == len(js))
    graph, edges = {}, 0
    for row in rows:
        _require(type(row) is dict and set(row) == {"path", "imports", "dynamic_imports", "css"})
        name = row["path"]
        _require(isinstance(name, str) and name in js and name not in graph)
        for key, allowed in (("imports", js), ("dynamic_imports", js), ("css", css)):
            edges += len(_names(row[key], allowed))
        graph[name] = row
    _require(list(graph) == sorted(js) and edges <= MAX_GRAPH_EDGES)
    _require(_closure(graph, dynamic=True) == files)
    entries = ["index.html", ENTRY_JS, *graph[ENTRY_JS]["css"]]
    return entries, sorted(_closure(graph))


def _validate_manifest(value, *, legacy=False):
    _require(type(value) is dict)
    if legacy and value.get("schema_version") == 1:
        _require(type(value["schema_version"]) is int
                 and set(value) == {"schema_version", "kind", "asset_set_sha256", "files"})
        _file_rows(value["files"], sorted_rows=False)
        _require([row["path"] for row in value["files"]] == list(LEGACY_ASSETS))
    else:
        _require(set(value) == {"schema_version", "kind", "asset_set_sha256", "files", "entry_files", "initial_files", "module_graph"}
                 and type(value["schema_version"]) is int and value["schema_version"] == 2)
        names = _file_rows(value["files"])
        entries, initial = _graph_fields(names, value["module_graph"])
        _require(value["entry_files"] == entries and value["initial_files"] == initial)
    _require(value["kind"] == "operator_console_static_build" and value["asset_set_sha256"] == _digest(value["files"]))
    return value


def _vite_graph(raw):
    source = _json(raw)
    _require(type(source) is dict and 1 <= len(source) <= MAX_ASSET_FILES)
    allowed = {"file", "src", "name", "isEntry", "isDynamicEntry", "imports", "dynamicImports", "css", "assets"}
    files, graph = {"index.html"}, {}
    entries = []
    for key, row in source.items():
        _require(isinstance(key, str) and 0 < len(key) <= 512 and type(row) is dict
                 and "file" in row and set(row) <= allowed and _safe_name(row["file"]))
        for field in ("src", "name"):
            if field in row:
                _require(isinstance(row[field], str) and 0 < len(row[field]) <= 512)
        for field in ("isEntry", "isDynamicEntry"):
            if field in row:
                _require(type(row[field]) is bool)
        # No images, maps, source files or other runtime formats are supported.
        _require(row.get("assets", []) == [])
        files.add(row["file"])
        if row.get("isEntry") is True and row["file"].endswith(".js"):
            entries.append((key, row["file"]))
    _require(entries == [("index.html", ENTRY_JS)])
    for row in source.values():
        name = row["file"]
        css = row.get("css", [])
        _require(type(css) is list and len(css) <= MAX_ASSET_FILES
                 and all(_safe_name(path) and path.endswith(".css") for path in css)
                 and len(css) == len(set(css)))
        files.update(css)
        refs = {}
        for field in ("imports", "dynamicImports"):
            values = row.get(field, [])
            _require(type(values) is list and len(values) <= MAX_ASSET_FILES
                     and all(isinstance(ref, str) and ref in source for ref in values)
                     and len(values) == len(set(values)))
            resolved = [source[ref]["file"] for ref in values]
            _require(all(path.endswith(".js") for path in resolved))
            refs[field] = sorted(resolved)
        if name.endswith(".js"):
            _require(name not in graph)
            graph[name] = {"path": name, "imports": refs["imports"], "dynamic_imports": refs["dynamicImports"], "css": sorted(css)}
        else:
            _require(name.endswith(".css") and not css and not refs["imports"] and not refs["dynamicImports"])
    rows = [graph[name] for name in sorted(graph)]
    entries, initial = _graph_fields(files, rows)
    _require(3 <= len(files) <= MAX_ASSET_FILES)
    return files, rows, entries, initial


def _license_header():
    notice = _read(ROOT / "THIRD_PARTY_NOTICES.txt", 16384).decode("utf-8")
    _require("*/" not in notice and "Permission is hereby granted" in notice)
    return ("/*!\n" + notice.rstrip() + "\n*/\n").encode("utf-8")


def _write(path, raw):
    descriptor, temporary_name = tempfile.mkstemp(prefix=".console-", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def build():
    """Publish only a bounded graph emitted by the explicit local Vite build."""
    inventory = _dist_layout(staging=True)
    raw_graph = _read(DIST / VITE_MANIFEST, MAX_VITE_MANIFEST_BYTES)
    names, graph, entries, initial = _vite_graph(raw_graph)
    _require(names <= set(inventory))
    assets = {name: _read(inventory[name]) for name in names}
    header = _license_header()
    for name, raw in list(assets.items()):
        if name.endswith(".js") and not raw.startswith(header):
            assets[name] = header + raw
    _require(all(0 < len(raw) <= MAX_ASSET_BYTES for raw in assets.values())
             and sum(map(len, assets.values())) <= MAX_TOTAL_BYTES)
    for raw in assets.values():
        raw.decode("utf-8")
    previous_path = DIST / MANIFEST
    previous = (_validate_manifest(_json(_read(previous_path, MAX_MANIFEST_BYTES)), legacy=True)
                if previous_path.exists() else None)
    old_rows = {row["path"]: row for row in previous["files"]} if previous else {}
    stale = sorted(set(inventory) - names)
    # Unknown files are never adopted or deleted. Only old recorded, unchanged
    # generated assets qualify for exact-file cleanup; there is no recursive rm.
    for name in stale:
        _require(name in old_rows and name.startswith("assets/"))
        raw = _read(inventory[name])
        _require(old_rows[name]["bytes"] == len(raw) and old_rows[name]["sha256"] == hashlib.sha256(raw).hexdigest())
    rows = _rows(assets)
    manifest = _validate_manifest({"schema_version": 2, "kind": "operator_console_static_build",
                "asset_set_sha256": _digest(rows), "files": rows, "entry_files": entries,
                "initial_files": initial, "module_graph": graph})
    encoded_manifest = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _require(len(encoded_manifest) <= MAX_MANIFEST_BYTES)
    for name, raw in assets.items():
        if name.endswith(".js"):
            _write(inventory[name], raw)
    for name in stale:
        path = inventory[name]
        _require(path.resolve().parent == (DIST / "assets").resolve())
        raw = _read(path)
        _require(old_rows[name]["bytes"] == len(raw) and old_rows[name]["sha256"] == hashlib.sha256(raw).hexdigest())
        path.unlink()
    _write(DIST / MANIFEST, encoded_manifest)
    _require(_read(DIST / VITE_MANIFEST, MAX_VITE_MANIFEST_BYTES) == raw_graph)
    (DIST / VITE_MANIFEST).unlink()
    _require(set(_dist_layout()) == names)
    return manifest


def read_dist():
    """Load one verified in-memory build. Requests never resolve disk paths."""
    inventory = _dist_layout()
    manifest = _validate_manifest(_json(_read(DIST / MANIFEST, MAX_MANIFEST_BYTES)))
    _require(set(inventory) == {row["path"] for row in manifest["files"]})
    assets = {name: _read(path) for name, path in inventory.items()}
    _require(manifest["files"] == _rows(assets))
    header = _license_header()
    for name, raw in assets.items():
        raw.decode("utf-8")
        if name.endswith(".js"):
            _require(raw.startswith(header))
    return assets


def main():
    argparse.ArgumentParser(description="Record only the bounded local operator-console asset graph").parse_args()
    try:
        manifest = build()
    except (BuildError, OSError, ValueError, TypeError):
        print("console_build_unavailable", file=sys.stderr)
        return 1
    print(json.dumps({"status": "console_built", "files": len(manifest["files"]),
                      "asset_set_sha256": manifest["asset_set_sha256"]}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
