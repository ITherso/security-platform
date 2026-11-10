"""Bounded single-file JSON input and explicit local path checks."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import stat

from .schema import (HandoffInput, InputError, MAX_DEPTH, MAX_INPUT_BYTES,
                     MAX_NODES, MAX_TEXT_BYTES, validate)


@dataclass(frozen=True, slots=True)
class LoadedInput:
    document: HandoffInput
    sha256: str
    byte_length: int


def _plain_stat(path: Path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        raise InputError("linked_path_not_allowed")
    return info


def check_existing_path(path: Path, *, directory: bool):
    """Inspect every component without first resolving away link evidence."""
    cursor = Path(path.anchor)
    for part in path.parts[1:]:
        cursor = cursor / part
        info = _plain_stat(cursor)
        if cursor != path and not stat.S_ISDIR(info.st_mode):
            raise InputError("invalid_parent_directory")
    info = _plain_stat(path)
    if directory and not stat.S_ISDIR(info.st_mode):
        raise InputError("directory_required")
    if not directory and not stat.S_ISREG(info.st_mode):
        raise InputError("regular_input_required")
    return info


def explicit_relative_path(raw: str) -> Path:
    if type(raw) is not str or not raw or len(raw) > 512 or "\x00" in raw:
        raise InputError("invalid_explicit_path")
    windows = PureWindowsPath(raw)
    if windows.drive or windows.root or Path(raw).is_absolute():
        raise InputError("relative_path_required")
    parts = raw.replace("\\", "/").split("/")
    reserved = {"CON", "PRN", "AUX", "NUL", *("COM" + str(i) for i in range(1, 10)),
                *("LPT" + str(i) for i in range(1, 10))}
    for part in parts:
        if part in ("", ".", "..") or part.endswith((" ", ".")) or any(c in part for c in '<>:"|?*'):
            raise InputError("unsafe_path_component")
        if part.split(".", 1)[0].upper() in reserved or any(ord(c) < 32 for c in part):
            raise InputError("unsafe_path_component")
    path = Path.cwd().joinpath(*parts)
    check_existing_path(Path.cwd(), directory=True)
    return path


def output_location(raw: str) -> Path:
    path = explicit_relative_path(raw)
    check_existing_path(path.parent, directory=True)
    if os.path.lexists(path):
        raise InputError("output_directory_must_be_new")
    return path


def _depth_check(text: str):
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise InputError("json_depth_limit")
        elif char in "]}":
            depth -= 1


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate_json_key")
        result[key] = value
    return result


def _integer(raw):
    if len(raw) > 20:
        raise InputError("integer_size_limit")
    return int(raw)


def _reject_number(_raw):
    raise InputError("non_integer_number_rejected")


def _tree_budget(value):
    stack = [value]
    nodes = text_bytes = 0
    while stack:
        item = stack.pop()
        nodes += 1
        if nodes > MAX_NODES:
            raise InputError("json_node_limit")
        if type(item) is str:
            try:
                encoded = item.encode("utf-8", "strict")
            except UnicodeError:
                raise InputError("invalid_unicode") from None
            if len(item) > 8192:
                raise InputError("json_string_limit")
            text_bytes += len(encoded)
            if text_bytes > MAX_TEXT_BYTES:
                raise InputError("json_text_budget")
        elif type(item) is dict:
            stack.extend(item.keys())
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)


def load_input(raw_path: str) -> LoadedInput:
    path = explicit_relative_path(raw_path)
    info = check_existing_path(path, directory=False)
    if path.suffix.lower() != ".json" or not 0 < info.st_size <= MAX_INPUT_BYTES:
        raise InputError("invalid_input_file_size_or_type")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise InputError("input_identity_changed")
        if getattr(opened, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise InputError("linked_path_not_allowed")
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not 0 < len(raw) <= MAX_INPUT_BYTES:
        raise InputError("input_size_limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("invalid_utf8") from None
    if text.startswith("\ufeff"):
        raise InputError("utf8_bom_not_supported")
    _depth_check(text)
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                           parse_float=_reject_number, parse_constant=_reject_number)
    except (json.JSONDecodeError, RecursionError):
        raise InputError("invalid_json") from None
    _tree_budget(value)
    return LoadedInput(validate(value), hashlib.sha256(raw).hexdigest(), len(raw))
