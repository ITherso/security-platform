import json
import time

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from security_platform.auth.operator_oidc import OperatorAuthenticationError, OperatorVerifier


@pytest.fixture
def identity(tmp_path):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public.update(kid="fixture-key", use="sig", alg="RS256", key_ops=["verify"])
    file = tmp_path / "jwks.json"
    file.write_text(json.dumps({"keys": [public]}))
    verifier = OperatorVerifier(issuer="https://issuer.example.test", audience="security-platform", jwks_file=file)
    now = int(time.time())
    claims = {"iss": "https://issuer.example.test", "aud": "security-platform", "sub": "operator-a",
              "client_id": "test-client", "jti": "test-token", "iat": now, "exp": now + 300}
    def token(*, changes=None, header=None, key=None, algorithm="RS256"):
        return jwt.encode({**claims, **(changes or {})}, key or private, algorithm=algorithm,
                          headers={"kid": "fixture-key", "typ": "at+jwt", **(header or {})})
    return verifier, token, claims, private, public, file


def test_real_signed_access_token_ignores_role_tenant_claims(identity):
    verifier, token, _, _, _, _ = identity
    principal = verifier.verify(token(changes={"roles": ["admin"], "tenant": "foreign", "is_admin": True}))
    assert principal.issuer == "https://issuer.example.test" and principal.subject == "operator-a"
    assert not hasattr(principal, "roles") and not hasattr(principal, "tenant")


@pytest.mark.parametrize("change", [
    {"iss": "https://attacker.example.test"}, {"aud": "other-api"}, {"sub": ""}, {"exp": 1},
    {"iat": 99999999999}, {"iat": True}, {"exp": 999999999999999999999999999999999999},
    {"exp": None}, {"client_id": ""}, {"jti": None}, {"nbf": 99999999999},
])
def test_invalid_claims_are_rejected(identity, change):
    verifier, token, *_ = identity
    with pytest.raises(OperatorAuthenticationError, match="invalid_operator_token"):
        verifier.verify(token(changes=change))


@pytest.mark.parametrize("header", [{"typ": "JWT"}, {"typ": "id+jwt"}, {"kid": "unknown"},
                                    {"jku": "https://attacker.example.test/keys"},
                                    {"x5u": "http://127.0.0.1/keys"}, {"crit": []}])
def test_token_header_never_selects_an_untrusted_key_source(identity, header, monkeypatch):
    verifier, token, *_ = identity
    import socket
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("key URL must not be fetched"))
    with pytest.raises(OperatorAuthenticationError):
        verifier.verify(token(header=header))


def test_wrong_signature_and_symmetric_algorithm_are_rejected(identity):
    verifier, token, claims, *_ = identity
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for bad in (token(key=other), jwt.encode(claims, "x" * 64, algorithm="HS256", headers={"kid": "fixture-key", "typ": "at+jwt"})):
        with pytest.raises(OperatorAuthenticationError):
            verifier.verify(bad)


@pytest.mark.parametrize("field", ["iss", "sub", "aud", "exp", "iat", "jti", "client_id"])
def test_profile_requires_every_mandatory_claim(identity, field):
    verifier, _, claims, private, *_ = identity
    claims.pop(field)
    token = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "fixture-key", "typ": "at+jwt"})
    with pytest.raises(OperatorAuthenticationError):
        verifier.verify(token)


def test_jwks_rotation_is_explicit_and_private_keys_are_rejected(identity):
    verifier, token, _, private, public, file = identity
    file.write_text(json.dumps({"keys": [{**public, "d": "must-not-load-private-material"}]}))
    with pytest.raises(ValueError):
        OperatorVerifier(issuer=verifier.issuer, audience=verifier.audience, jwks_file=file)
    assert verifier.verify(token()).subject == "operator-a"


def test_duplicate_and_oversized_jwks_are_rejected(identity):
    verifier, _, _, _, public, file = identity
    file.write_text(json.dumps({"keys": [public, public]}))
    with pytest.raises(ValueError):
        OperatorVerifier(issuer=verifier.issuer, audience=verifier.audience, jwks_file=file)
    file.write_bytes(b"x" * 65537)
    with pytest.raises(ValueError):
        OperatorVerifier(issuer=verifier.issuer, audience=verifier.audience, jwks_file=file)
