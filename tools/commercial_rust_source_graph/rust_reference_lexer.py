"""Bounded lexical boundaries only; this is not a Rust parser or compiler."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
import hashlib
import re

from .source_graph_contracts import InputError, diagnostic_identifier


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int
    end: int
    line: int
    column: int
    value: str | None = field(default=None, repr=False)
    raw_identifier: bool = False

    @property
    def position(self) -> dict:
        return {"byte_offset": self.start, "line": self.line, "column": self.column}


@dataclass(frozen=True)
class LexResult:
    source_id: str
    source_sha256: str
    tokens: tuple[Token, ...] = field(repr=False)
    matching: tuple[int, ...] = field(repr=False)
    summary: dict
    diagnostics: tuple[dict, ...]


class _Boundary(Exception):
    def __init__(self, code: str, index: int):
        self.code, self.index = code, index


_LIMITS = {"max_tokens_per_file": 400000, "max_delimiter_depth": 128,
           "max_comment_depth": 64, "max_raw_hashes": 64}
_COUNTERS = ("line_comment_count", "block_comment_count", "string_literal_count",
             "raw_string_literal_count", "byte_string_literal_count", "raw_byte_string_literal_count",
             "character_literal_count", "lifetime_count", "maximum_delimiter_depth",
             "maximum_comment_depth", "maximum_raw_hashes")
_PUNCTUATION = frozenset(";:,=.!?+-*/%&|^<>@#$~")
_SIMPLE_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "\\": "\\", '"': '"', "'": "'"}
_HEX = frozenset("0123456789abcdefABCDEF")


def _limits(value: dict | None) -> dict:
    result = dict(_LIMITS)
    if value is not None:
        if type(value) is not dict:
            raise InputError("rust_source_invalid_lexical_limits")
        for key, maximum in _LIMITS.items():
            selected = value.get(key, maximum)
            if type(selected) is not int or not 0 < selected <= maximum:
                raise InputError("rust_source_invalid_lexical_limit")
            result[key] = selected
    return result


def _identifier_start(char: str) -> bool:
    return char == "_" or "a" <= char <= "z" or "A" <= char <= "Z"


def _identifier_part(char: str) -> bool:
    return _identifier_start(char) or "0" <= char <= "9"


def _escape(text: str, index: int, *, byte: bool, continuation: bool) -> tuple[int, str]:
    if index + 1 >= len(text):
        raise _Boundary("lexical_boundary_unresolved", index)
    char = text[index + 1]
    if char in _SIMPLE_ESCAPES:
        return index + 2, _SIMPLE_ESCAPES[char]
    if char == "x":
        digits = text[index + 2:index + 4]
        if len(digits) != 2 or any(item not in _HEX for item in digits):
            raise _Boundary("unsupported_lexical_construct", index)
        value = int(digits, 16)
        if not byte and value > 127:
            raise _Boundary("unsupported_lexical_construct", index)
        return index + 4, chr(value)
    if char == "u" and not byte and text[index + 2:index + 3] == "{":
        end = text.find("}", index + 3, index + 16)
        raw_digits = "" if end < 0 else text[index + 3:end]
        digits = raw_digits.replace("_", "")
        if (not raw_digits or raw_digits[0] not in _HEX or not 1 <= len(digits) <= 6
                or any(item not in _HEX for item in digits)):
            raise _Boundary("unsupported_lexical_construct", index)
        value = int(digits, 16)
        if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
            raise _Boundary("unsupported_lexical_construct", index)
        return end + 1, chr(value)
    if continuation and char in "\r\n":
        cursor = index + 2
        if char == "\r" and text[cursor:cursor + 1] == "\n":
            cursor += 1
        while cursor < len(text) and text[cursor] in " \t\r\n":
            cursor += 1
        return cursor, ""
    raise _Boundary("unsupported_lexical_construct", index)


def _quoted(text: str, quote: int, *, byte: bool) -> tuple[int, str]:
    cursor, value = quote + 1, []
    while cursor < len(text):
        char = text[cursor]
        if char == '"':
            return cursor + 1, "".join(value)
        if char == "\\":
            cursor, decoded = _escape(text, cursor, byte=byte, continuation=True)
            value.append(decoded)
        else:
            if byte and ord(char) > 127:
                raise _Boundary("unsupported_lexical_construct", cursor)
            value.append(char)
            cursor += 1
    raise _Boundary("lexical_boundary_unresolved", quote)


def _character(text: str, quote: int, *, byte: bool) -> tuple[int, str]:
    cursor = quote + 1
    if cursor >= len(text):
        raise _Boundary("lexical_boundary_unresolved", quote)
    if text[cursor] == "\\":
        cursor, value = _escape(text, cursor, byte=byte, continuation=False)
    else:
        value = text[cursor]
        cursor += 1
        if value in "\r\n'" or byte and ord(value) > 127:
            raise _Boundary("unsupported_lexical_construct", quote)
    if len(value) != 1 or text[cursor:cursor + 1] != "'":
        raise _Boundary("unsupported_lexical_construct", quote)
    return cursor + 1, value


def lex_source(raw: bytes, source_identity: dict, limits: dict | None = None) -> LexResult:
    """No I/O. Tokens and decoded literals are ephemeral, never output payloads."""
    limits = _limits(limits)
    expected = {"source_id", "root_id", "pinned_commit", "path", "observed_bytes", "observed_sha256"}
    if (type(source_identity) is not dict or set(source_identity) != expected
            or type(raw) is not bytes or len(raw) > 512 * 1024
            or type(source_identity["observed_bytes"]) is not int
            or len(raw) != source_identity["observed_bytes"]
            or hashlib.sha256(raw).hexdigest() != source_identity["observed_sha256"]
            or type(source_identity["source_id"]) is not str
            or re.fullmatch(r"RSF[0-9]{4}", source_identity["source_id"]) is None):
        raise InputError("rust_source_lexical_identity_mismatch")
    source_id, sha = source_identity["source_id"], source_identity["observed_sha256"]
    counts = {key: 0 for key in _COUNTERS}
    summary = {"source_file_reference": source_id, "source_sha256": sha,
               "lexical_status": "lexically_bounded", "scan_complete": True,
               "token_count": 0, "line_count": 1, "crlf_count": 0, **counts,
               "opaque_macro_tree_count": 0, "reference_count": 0, "condition_count": 0, "diagnostic_count": 0}
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        diagnostic = {"source_file_reference": source_id, "source_sha256": sha,
                      "position": {"byte_offset": error.start, "line": 1, "column": 1},
                      "byte_end": min(error.start + 1, len(raw)), "code": "unsupported_lexical_construct",
                      "reference_id": None, "lexical_scope": []}
        diagnostic["diagnostic_id"] = diagnostic_identifier(diagnostic)
        summary.update(lexical_status="unsupported_lexical_construct", scan_complete=False, diagnostic_count=1)
        return LexResult(source_id, sha, (), (), summary, (diagnostic,))
    offsets, line_starts = [0], [0]
    for index, char in enumerate(text):
        offsets.append(offsets[-1] + len(char.encode("utf-8")))
        if char == "\n" or char == "\r" and text[index + 1:index + 2] != "\n":
            line_starts.append(index + 1)
    summary.update(line_count=len(line_starts), crlf_count=text.count("\r\n"))
    tokens, matching, stack = [], [], []

    def emit(kind, content, start, end, value=None, raw_identifier=False):
        if len(tokens) >= limits["max_tokens_per_file"]:
            raise InputError("rust_source_token_limit_exceeded")
        line = bisect_right(line_starts, start)
        tokens.append(Token(kind, content, offsets[start], offsets[end], line,
                            start - line_starts[line - 1] + 1, value, raw_identifier))
        matching.append(-1)
        if kind == "punctuation" and content in "([{":
            if len(stack) >= limits["max_delimiter_depth"]:
                raise InputError("rust_source_delimiter_limit_exceeded")
            stack.append((content, len(tokens) - 1))
            counts["maximum_delimiter_depth"] = max(counts["maximum_delimiter_depth"], len(stack))
        elif kind == "punctuation" and content in ")]}":
            if not stack or stack[-1][0] != {")": "(", "]": "[", "}": "{"}[content]:
                raise _Boundary("lexical_boundary_unresolved", start)
            _opening, prior = stack.pop()
            matching[prior], matching[-1] = len(tokens) - 1, prior

    cursor = 0
    try:
        if text.startswith("\ufeff"):
            raise _Boundary("unsupported_lexical_construct", 0)
        if text.startswith("#!") and not text.startswith("#!["):
            # Script shebangs are outside this subset, not Rust source tokens.
            raise _Boundary("unsupported_lexical_construct", 0)
        while cursor < len(text):
            start, char = cursor, text[cursor]
            if char in " \t\r\n":
                cursor += 1
                continue
            if text.startswith("//", cursor):
                counts["line_comment_count"] += 1
                cursor += 2
                while cursor < len(text) and text[cursor] not in "\r\n":
                    cursor += 1
                continue
            if text.startswith("/*", cursor):
                counts["block_comment_count"] += 1
                cursor, depth = cursor + 2, 1
                counts["maximum_comment_depth"] = max(counts["maximum_comment_depth"], depth)
                while cursor < len(text) and depth:
                    if text.startswith("/*", cursor):
                        depth += 1
                        if depth > limits["max_comment_depth"]:
                            raise InputError("rust_source_comment_depth_limit_exceeded")
                        counts["maximum_comment_depth"] = max(counts["maximum_comment_depth"], depth)
                        cursor += 2
                    elif text.startswith("*/", cursor):
                        depth -= 1
                        cursor += 2
                    else:
                        cursor += 1
                if depth:
                    raise _Boundary("lexical_boundary_unresolved", start)
                continue
            raw_prefix = 2 if text.startswith("br", cursor) else 1 if char == "r" else 0
            if raw_prefix:
                quote, hashes = cursor + raw_prefix, 0
                while text[quote:quote + 1] == "#":
                    hashes, quote = hashes + 1, quote + 1
                    if hashes > limits["max_raw_hashes"]:
                        raise InputError("rust_source_raw_hash_limit_exceeded")
                if text[quote:quote + 1] == '"':
                    close = text.find('"' + "#" * hashes, quote + 1)
                    if close < 0:
                        raise _Boundary("lexical_boundary_unresolved", start)
                    value = text[quote + 1:close]
                    byte = raw_prefix == 2
                    if byte and any(ord(item) > 127 for item in value):
                        raise _Boundary("unsupported_lexical_construct", start)
                    cursor = close + 1 + hashes
                    counts["maximum_raw_hashes"] = max(counts["maximum_raw_hashes"], hashes)
                    counts["raw_byte_string_literal_count" if byte else "raw_string_literal_count"] += 1
                    emit("byte_string" if byte else "string", "", start, cursor, value)
                    continue
                if hashes and not (raw_prefix == 1 and hashes == 1 and quote < len(text)
                                   and _identifier_start(text[quote])):
                    raise _Boundary("unsupported_lexical_construct", start)
            if char == '"' or text.startswith('b"', cursor):
                byte = char == "b"
                cursor, value = _quoted(text, cursor + (1 if byte else 0), byte=byte)
                counts["byte_string_literal_count" if byte else "string_literal_count"] += 1
                emit("byte_string" if byte else "string", "", start, cursor, value)
                continue
            if text.startswith("b'", cursor):
                cursor, value = _character(text, cursor + 1, byte=True)
                counts["character_literal_count"] += 1
                emit("character", "", start, cursor, value)
                continue
            if char == "'":
                end = cursor + 1
                if end < len(text) and _identifier_start(text[end]):
                    end += 1
                    while end < len(text) and _identifier_part(text[end]):
                        end += 1
                    if text[end:end + 1] != "'":
                        if text[end:end + 1] == "#":
                            # Raw/otherwise unsupported lifetime forms must not
                            # expose their suffix as ordinary source tokens.
                            raise _Boundary("unsupported_lexical_construct", start)
                        counts["lifetime_count"] += 1
                        emit("lifetime", text[cursor:end], start, end)
                        cursor = end
                        continue
                cursor, value = _character(text, cursor, byte=False)
                counts["character_literal_count"] += 1
                emit("character", "", start, cursor, value)
                continue
            if _identifier_start(char):
                raw_identifier = text.startswith("r#", cursor)
                cursor += 2 if raw_identifier else 0
                word = cursor
                if cursor >= len(text) or not _identifier_start(text[cursor]):
                    raise _Boundary("unsupported_lexical_construct", start)
                cursor += 1
                while cursor < len(text) and _identifier_part(text[cursor]):
                    cursor += 1
                name = text[word:cursor]
                if len(name) > 128:
                    raise InputError("rust_source_identifier_limit_exceeded")
                if not raw_identifier and name in ("c", "cr") and text[cursor:cursor + 1] in ('"', "#"):
                    raise _Boundary("unsupported_lexical_construct", start)
                emit("identifier", name, start, cursor, raw_identifier=raw_identifier)
                continue
            if "0" <= char <= "9":
                cursor += 1
                while cursor < len(text):
                    current = text[cursor]
                    if _identifier_part(current):
                        cursor += 1
                    elif current == "." and text[cursor + 1:cursor + 2].isdigit():
                        cursor += 1
                    elif current in "+-" and text[cursor - 1] in "eE":
                        cursor += 1
                    else:
                        break
                emit("number", "", start, cursor)
                continue
            if char in _PUNCTUATION or char in "()[]{}":
                cursor += 1
                emit("punctuation", char, start, cursor)
                continue
            raise _Boundary("unsupported_lexical_construct", cursor)
        if stack:
            raise _Boundary("lexical_boundary_unresolved", len(text))
    except _Boundary as error:
        index = min(error.index, len(text))
        line = bisect_right(line_starts, index)
        diagnostic = {"source_file_reference": source_id, "source_sha256": sha,
                      "position": {"byte_offset": offsets[index], "line": line,
                                   "column": index - line_starts[line - 1] + 1},
                      "byte_end": offsets[min(index + 1, len(text))], "code": error.code,
                      "reference_id": None, "lexical_scope": []}
        diagnostic["diagnostic_id"] = diagnostic_identifier(diagnostic)
        summary.update(lexical_status=error.code, scan_complete=False, diagnostic_count=1)
        return LexResult(source_id, sha, (), (), summary, (diagnostic,))
    summary.update(counts)
    summary["token_count"] = len(tokens)
    return LexResult(source_id, sha, tuple(tokens), tuple(matching), summary, ())


__all__ = ("Token", "LexResult", "lex_source")
