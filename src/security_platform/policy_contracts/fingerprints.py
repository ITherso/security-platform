"""Versioned content identities. None is a signature, authority or readback proof."""
import hashlib
import json

from .immutable import FrozenObject, thaw

BUNDLE_FINGERPRINT_PREFIX = "sp-hbf-bundle-v1:sha256:"
ADAPTER_FINGERPRINT_PREFIX = "sp-hbf-adapter-v1:sha256:"
PREVIEW_FINGERPRINT_PREFIX = "sp-hbf-preview-v1:sha256:"
BUNDLE_PATTERN = r"^sp-hbf-bundle-v1:sha256:[a-f0-9]{64}$"
ADAPTER_PATTERN = r"^sp-hbf-adapter-v1:sha256:[a-f0-9]{64}$"
PREVIEW_PATTERN = r"^sp-hbf-preview-v1:sha256:[a-f0-9]{64}$"


def canonical_bytes(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, FrozenObject):
        value = thaw(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _fingerprint(prefix, value):
    return prefix + hashlib.sha256(canonical_bytes(value)).hexdigest()


def bundle_fingerprint(bundle):
    """Preview uses normalized bundles; raw-bundle hashes are diagnostic only.

    Ordered zones, CIDRs and policies remain arrays and are never sorted. Object
    key order is irrelevant only because runtime zone order is explicit here.
    """
    return _fingerprint(BUNDLE_FINGERPRINT_PREFIX, bundle)


def adapter_fingerprint(identity):
    return _fingerprint(ADAPTER_FINGERPRINT_PREFIX, identity)


def preview_fingerprint(binding):
    return _fingerprint(PREVIEW_FINGERPRINT_PREFIX, binding)
