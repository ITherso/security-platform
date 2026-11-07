"""Record/check the fixed Vite output asset set. Does not execute tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
ASSETS = ("index.html", "assets/console.js", "assets/console.css")
MANIFEST = "build-manifest.json"
MAX_ASSET_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024


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


def _rows(assets):
    return [{"path": name, "bytes": len(assets[name]), "sha256": hashlib.sha256(assets[name]).hexdigest()}
            for name in ASSETS]


def _digest(rows):
    encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dist_layout():
    _plain(DIST, directory=True)
    for path in DIST.iterdir():
        _require(path.name in {"index.html", "assets", MANIFEST})
        _plain(path, directory=path.name == "assets")
    source = DIST / "assets"
    if source.exists():
        allowed = {Path(name).name for name in ASSETS if name.startswith("assets/")}
        for path in source.iterdir():
            _require(path.name in allowed)
            _plain(path)


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
    """Capture every fixed Vite output before writing its integrity manifest."""
    _dist_layout()
    assets = {name: _read(DIST / name) for name in ASSETS}
    _require(sum(map(len, assets.values())) <= MAX_TOTAL_BYTES)
    for raw in assets.values():
        raw.decode("utf-8")
    rows = _rows(assets)
    manifest = {"schema_version": 1, "kind": "operator_console_static_build",
                "asset_set_sha256": _digest(rows), "files": rows}
    _plain(ROOT, directory=True)
    if DIST.exists():
        _dist_layout()
    else:
        DIST.mkdir()
    _write(DIST / MANIFEST, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return manifest


def read_dist():
    """Load one verified in-memory build. Requests never resolve disk paths."""
    _dist_layout()
    raw_manifest = _read(DIST / MANIFEST, 16384)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result)
            result[key] = value
        return result
    manifest = json.loads(raw_manifest, object_pairs_hook=unique)
    _require(isinstance(manifest, dict) and set(manifest) == {"schema_version", "kind", "asset_set_sha256", "files"})
    _require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1
        and manifest["kind"] == "operator_console_static_build")
    assets = {name: _read(DIST / name) for name in ASSETS}
    _require(sum(map(len, assets.values())) <= MAX_TOTAL_BYTES)
    rows = _rows(assets)
    _require(manifest["files"] == rows and manifest["asset_set_sha256"] == _digest(rows))
    # Explicit type checks prevent JSON booleans from being treated as integer sizes.
    _require(all(type(row) is dict and type(row.get("bytes")) is int for row in manifest["files"]))
    return assets


def main():
    argparse.ArgumentParser(description="Build only the fixed local operator-console assets").parse_args()
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
