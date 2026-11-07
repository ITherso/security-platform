"""Bounded immutable JSON trees; no hidden mutable dictionaries or lists."""
from collections.abc import Mapping
from dataclasses import dataclass
import math

from .errors import PolicyContractError

MAX_NODES, MAX_DEPTH, MAX_TEXT = 50000, 20, 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class FrozenObject(Mapping):
    _pairs: tuple

    def __iter__(self):
        return (key for key, _ in self._pairs)

    def __len__(self):
        return len(self._pairs)

    def items(self):
        return iter(self._pairs)

    def values(self):
        return (value for _, value in self._pairs)

    def __getitem__(self, key):
        for name, value in self._pairs:
            if name == key:
                return value
        raise KeyError(key)


def freeze_object(value):
    if not isinstance(value, (dict, FrozenObject)):
        raise PolicyContractError("invalid_policy_bundle")
    nodes = text = 0
    def visit(item, depth):
        nonlocal nodes, text
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise PolicyContractError("input_limit_exceeded")
        if isinstance(item, (dict, FrozenObject)):
            pairs = []
            seen = set()
            for key, child in item.items():
                if not isinstance(key, str) or key in seen:
                    raise PolicyContractError("invalid_policy_bundle")
                seen.add(key)
                text += len(key.encode("utf-8"))
                pairs.append((key, visit(child, depth + 1)))
            result = FrozenObject(tuple(pairs))
        elif isinstance(item, (list, tuple)):
            result = tuple(visit(child, depth + 1) for child in item)
        elif isinstance(item, str):
            text += len(item.encode("utf-8"))
            result = item
        elif item is None or type(item) is bool:
            result = item
        elif type(item) is int and item.bit_length() <= 256:
            result = item
        elif type(item) is float and math.isfinite(item):
            result = item
        else:
            raise PolicyContractError("invalid_policy_bundle")
        if text > MAX_TEXT:
            raise PolicyContractError("input_limit_exceeded")
        return result
    try:
        return visit(value, 0)
    except (UnicodeError, RecursionError) as exc:
        raise PolicyContractError("invalid_policy_bundle") from exc


def thaw(value):
    if isinstance(value, FrozenObject):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


def immutable_tuple(value):
    if not isinstance(value, (list, tuple)):
        raise PolicyContractError("invalid_contract")
    return tuple(value)
