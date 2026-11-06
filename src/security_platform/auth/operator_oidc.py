"""RS256 RFC 9068 access tokens verified with a fixed local public JWKS.

No discovery, key URL retrieval or membership provisioning takes place here.
Key rotation requires replacing the trusted file and restarting the service.
"""
import json
from pathlib import Path
import re

import jwt

from .principals import OperatorPrincipal


class OperatorAuthenticationError(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


class OperatorVerifier:
    def __init__(self, *, issuer, audience, jwks_file):
        self.issuer, self.audience = issuer, audience
        file = Path(jwks_file)
        if not file.is_file() or file.stat().st_size > 65536:
            raise ValueError("A bounded public JWKS file is required")
        with file.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("Public JWKS exceeds its limit")
        data = json.loads(raw, object_pairs_hook=_unique, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite")))
        if not isinstance(data, dict) or set(data) != {"keys"} or not isinstance(data["keys"], list) or not 1 <= len(data["keys"]) <= 16:
            raise ValueError("Invalid public JWKS")
        keys = {}
        for item in data["keys"]:
            if (not isinstance(item, dict) or item.get("kty") != "RSA" or item.get("alg") != "RS256"
                    or item.get("use") != "sig" or any(name in item for name in ("d", "p", "q", "dp", "dq", "qi", "oth", "k", "jku", "x5u"))
                    or item.get("key_ops", ["verify"]) != ["verify"]
                    or not isinstance(item.get("kid"), str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", item["kid"])
                    or item["kid"] in keys):
                raise ValueError("Invalid public verification key")
            key = jwt.PyJWK.from_dict(item, algorithm="RS256").key
            if not 2048 <= key.key_size <= 8192:
                raise ValueError("Invalid RSA verification key size")
            keys[item["kid"]] = key
        self._keys = keys

    def verify(self, token):
        try:
            if not isinstance(token, str) or not 1 <= len(token) <= 16384:
                raise ValueError()
            header = jwt.get_unverified_header(token)
            if (header.get("alg") != "RS256" or header.get("typ") not in {"at+jwt", "application/at+jwt"}
                    or any(name in header for name in ("jku", "x5u", "crit", "b64", "jwk"))
                    or header.get("kid") not in self._keys):
                raise ValueError()
            claims = jwt.decode(token, self._keys[header["kid"]], algorithms=["RS256"],
                issuer=self.issuer, audience=self.audience, leeway=30,
                options={"require": ["iss", "aud", "sub", "exp", "iat", "jti", "client_id"]})
            for key in ("exp", "iat", "nbf"):
                if key in claims and (type(claims[key]) is not int or not 0 <= claims[key] < 253402300799):
                    raise ValueError()
            if not 0 < claims["exp"] - claims["iat"] <= 3600:
                raise ValueError()
            if "nbf" in claims and claims["nbf"] > claims["exp"]:
                raise ValueError()
            for name, maximum in (("sub", 256), ("client_id", 128), ("jti", 128)):
                if not isinstance(claims[name], str) or not 1 <= len(claims[name]) <= maximum:
                    raise ValueError()
            return OperatorPrincipal(self.issuer, claims["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, OverflowError):
            raise OperatorAuthenticationError("invalid_operator_token") from None
