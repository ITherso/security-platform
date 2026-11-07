"""Reject equal-prefix ties without modifying the legacy zone resolver."""
import ipaddress

from .errors import PolicyContractError


def ensure_unambiguous_zones(bundle):
    seen = {}
    for zone in bundle.ordered_zones:
        for value in zone.cidrs:
            try:
                network = ipaddress.ip_network(value, strict=False)
            except ValueError as exc:
                raise PolicyContractError("invalid_policy_bundle") from exc
            key = network.version, int(network.network_address), network.prefixlen
            other = seen.setdefault(key, zone.name)
            if other != zone.name:
                raise PolicyContractError("ambiguous_equal_prefix_zones")
    return None


validate_zone_safety = ensure_unambiguous_zones
