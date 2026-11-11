"""Verify only a fixed, reviewed source subset; never load Termivar code."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess

from commercial_handoff.input_loader import check_existing_path
from .scope_contracts import InputError


PINNED_COMMIT = "6a2639348c2366d0bf71b9a34e5484d40aa393a3"
MAX_SOURCE_FILE_BYTES = 4 * 1024 * 1024
MAX_SOURCE_TOTAL_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class SourceFile:
    id: str
    path: str
    byte_length: int
    sha256: str


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    commit: str
    files: tuple[SourceFile, ...]


# These are measured file bytes at the pinned checkout, not dynamically chosen
# proposal paths.  Updating this finite subset requires a separate source review.
SOURCE_FILES = (
    SourceFile("termivar_cli_capabilities", "crates/termivar-cli/src/capabilities.rs", 116132, "dabd68ccbfd4144243d12b49fb741f7bef0438ca60a4e16b13fb479d6f483f2a"),
    SourceFile("termivar_cli_main", "crates/termivar-cli/src/main.rs", 279631, "c96f2e3a27be6f1ecbbbcaae539c3b9ec87253c25d0043b2891f9a6621ec0bff"),
    SourceFile("termivar_cli_cargo", "crates/termivar-cli/Cargo.toml", 4774, "7a6205bb33518ffc984a378a860fb22436b410b1e0e879c5f1bc1be90ffb59e4"),
    SourceFile("termivar_scan_profile", "crates/termivar-scanner/src/web_runtime/scan_profile.rs", 48159, "17ecc52399ac3f4df7cad46c17c66f6fc1777ed95847c48d999ee0be0774e386"),
    SourceFile("termivar_web_assessment", "crates/termivar-scanner/src/web_runtime/web_assessment.rs", 387204, "d055d9d19af335420dcf54bd0544889ba1237d341566de3b1421529f1eebd103"),
    SourceFile("termivar_assessment_passive", "crates/termivar-scanner/src/web_runtime/assessment_passive.rs", 134870, "f37a1620eb6e578b340a11e6b1cc44e5c7528e132c4ce441f9466fcb52af3445"),
    SourceFile("termivar_assessment_item", "crates/termivar-scanner/src/web_runtime/assessment_item.rs", 90315, "a23a91eeb13ae0c7dd5047a4ea4a3bd461f62b43f221930de896eb3c42eb7aa7"),
    SourceFile("termivar_graphql_catalog", "crates/termivar-scanner/src/graphql_review.rs", 83184, "ca8d0f8fe78c135e7c92ca742df37d1660d69acafcd259a4e2d3c3e480849522"),
    SourceFile("termivar_graphql_runtime", "crates/termivar-scanner/src/web_runtime/graphql_runtime.rs", 92733, "3f30b069dc1fc83f71a190cb2edfe4600520ab2515519a34960d7c7bb01f6952"),
    SourceFile("termivar_openapi_runtime", "crates/termivar-scanner/src/web_runtime/openapi_runtime.rs", 98310, "fd37dccdc8862f5b00ab581697a8437a1aa5217a6841b42eb5a5df32d3ad105c"),
    SourceFile("termivar_rest_runtime", "crates/termivar-scanner/src/web_runtime/rest_runtime.rs", 104902, "8b8a73def6349fdf9ef2e7c93ab18b188fd4e115e450d2b20a6b1837616c21b3"),
    SourceFile("termivar_resource_authorization_runtime", "crates/termivar-scanner/src/web_runtime/resource_authorization_runtime.rs", 103851, "e9164b9ec15514974dcc59f10de8eee2f2e6c7ae0e6b694c8287e7cf62babbdb"),
    SourceFile("termivar_root_api_visibility", "crates/termivar-scanner/src/web_runtime/assessment_api_visibility.rs", 11617, "6daeca81e260a4a5a26125c559ec2848a56b38fe1a74b502eb6569757ecbcbde"),
    SourceFile("termivar_reporting_contract", "docs/reporting.md", 34152, "3e61d4ec5f8397341bb1cf45de21bc50090735e9a461d4f94adf3dcc8381fdf2"),
    SourceFile("termivar_http_policy", "crates/termivar-scanner/src/http_evidence/policy.rs", 9990, "7180a848a29d693fd604d707b354c2dc6d4fc644c08423db3deba6842e1d07a0"),
    SourceFile("termivar_discovery", "crates/termivar-scanner/src/web_runtime/web_assessment/discovery.rs", 26415, "c6012e1f717495adad86ea90e3530f891c7331b7cebe1edc2fd0d6aad3760257"),
    SourceFile("termivar_request_broker", "crates/termivar-scanner/src/http_evidence/request_broker.rs", 156889, "c7f3d6db452e2ebbd07268a935b965fca74aa30892102439cb997147a38eaf38"),
)
SOURCE_IDS = tuple(item.id for item in SOURCE_FILES)


def validate_snapshot(snapshot: SourceSnapshot) -> None:
    """Check the prepared identity shape without reopening or executing sources."""
    if (type(snapshot) is not SourceSnapshot
            or snapshot.commit != PINNED_COMMIT
            or type(snapshot.files) is not tuple
            or snapshot.files != SOURCE_FILES
            or any(type(item) is not SourceFile for item in snapshot.files)):
        raise InputError("source_version_mismatch")


def _git_head(root: Path) -> str:
    # Only Git metadata is queried. No native Termivar command, status, hook,
    # source import, shell, network operation or proposal-controlled argument.
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith("GIT_"):
            del environment[name]
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), "rev-parse", "HEAD"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=10, check=False,
            shell=False, env=environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        raise InputError("source_version_mismatch") from None
    if result.returncode != 0 or result.stdout not in (
            (PINNED_COMMIT + "\n").encode("ascii"),
            (PINNED_COMMIT + "\r\n").encode("ascii")):
        raise InputError("source_version_mismatch")
    return PINNED_COMMIT


def _read_source(root: Path, expected: SourceFile) -> SourceFile:
    path = root.joinpath(*expected.path.split("/"))
    checked = check_existing_path(path, directory=False)
    if not 0 < checked.st_size <= MAX_SOURCE_FILE_BYTES:
        raise InputError("source_version_mismatch")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (checked.st_dev, checked.st_ino)
                or getattr(opened, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("source_version_mismatch")
        raw = stream.read(MAX_SOURCE_FILE_BYTES + 1)
    if len(raw) != expected.byte_length or hashlib.sha256(raw).hexdigest() != expected.sha256:
        raise InputError("source_version_mismatch")
    return SourceFile(expected.id, expected.path, len(raw), hashlib.sha256(raw).hexdigest())


def verify_sources(explicit_root: str | Path) -> SourceSnapshot:
    """Read the explicit trusted checkout and fail before any plan publication.

    This binds selected source bytes and HEAD only. It does not attest Git's
    producer, the whole tree, a compiled binary, or successful runtime behavior.
    The caller serializes no absolute root, machine path, environment or time.
    """
    try:
        raw_root = os.fspath(explicit_root)
        if (type(raw_root) is not str or not raw_root or len(raw_root) > 4096
                or "\x00" in raw_root or raw_root.startswith(("\\\\", "//"))):
            raise InputError("source_version_mismatch")
        root = Path(raw_root)
        if not root.is_absolute() or any(part == ".." for part in root.parts):
            raise InputError("source_version_mismatch")
        check_existing_path(root, directory=True)
        _git_head(root)
        measured = tuple(_read_source(root, item) for item in SOURCE_FILES)
        if sum(item.byte_length for item in measured) > MAX_SOURCE_TOTAL_BYTES:
            raise InputError("source_version_mismatch")
        _git_head(root)
    except (OSError, ValueError, TypeError) as error:
        if type(error) is InputError:
            raise
        raise InputError("source_version_mismatch") from None
    snapshot = SourceSnapshot(PINNED_COMMIT, measured)
    validate_snapshot(snapshot)
    return snapshot


def source_snapshot_to_dict(snapshot: SourceSnapshot) -> dict:
    validate_snapshot(snapshot)
    return {
        "commit": snapshot.commit,
        "files": [{"path": item.path, "bytes": item.byte_length, "sha256": item.sha256}
                  for item in snapshot.files],
    }
