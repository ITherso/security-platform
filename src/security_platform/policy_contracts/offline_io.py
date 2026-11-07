"""Explicit offline CLI file boundary. Never imported by the pure evaluator."""
import json
import math
import os
from pathlib import Path
import stat
import tempfile


MAX_INPUT_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


class OfflineInputError(ValueError):
    """Fixed public reason code; policy contents stay in the selected file."""


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise OfflineInputError("offline_input_invalid")
        result[key] = value
    return result


def _number(text):
    value = float(text)
    if not math.isfinite(value):
        raise OfflineInputError("offline_input_invalid")
    return value


def _constant(text):
    raise OfflineInputError("offline_input_invalid")


def read_input(path):
    try:
        with Path(path).open("rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise OfflineInputError("offline_input_invalid")
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise OfflineInputError("offline_input_too_large")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                           parse_float=_number, parse_constant=_constant)
        if not isinstance(value, dict):
            raise OfflineInputError("offline_input_invalid")
        stack, nodes = [(value, 0)], 0
        while stack:
            current, depth = stack.pop()
            nodes += 1
            if depth > 24 or nodes > 110000:
                raise OfflineInputError("offline_input_too_complex")
            if isinstance(current, dict):
                stack.extend((item, depth + 1) for item in current.values())
            elif isinstance(current, list):
                stack.extend((item, depth + 1) for item in current)
        return value
    except OfflineInputError:
        raise
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise OfflineInputError("offline_input_invalid") from exc


def write_output(path, value, *, input_path):
    """Replace only the explicitly selected output, after complete serialization."""
    temporary = None
    try:
        target = Path(path)
        if target.resolve() == Path(input_path).resolve():
            raise OfflineInputError("offline_output_is_input")
        raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2,
                          allow_nan=False) + "\n").encode("utf-8")
        if len(raw) > MAX_OUTPUT_BYTES:
            raise OfflineInputError("offline_output_too_large")
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".security-policy-", suffix=".tmp",
                                         dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
    except OfflineInputError:
        raise
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise OfflineInputError("offline_output_unavailable") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
