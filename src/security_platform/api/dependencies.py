from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from security_platform.auth.operator_oidc import OperatorAuthenticationError
from security_platform.services.enrollment import authenticate_device, authenticate_grant


def get_session(request: Request):
    # Commit/audit failures must happen before any successful response is sent.
    with request.app.state.database.session() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session, scope="function")]
_operator_scheme = HTTPBearer(auto_error=False, scheme_name="OperatorAccessToken", bearerFormat="JWT",
    description="RS256 RFC 9068 API access token. Tenant roles come from current database memberships.")
_enrollment_scheme = HTTPBearer(auto_error=False, scheme_name="EnrollmentGrant", bearerFormat="opaque",
    description="Single-use enrollment grant; valid only for device enrollment.")
_device_scheme = HTTPBearer(auto_error=False, scheme_name="DeviceCredential", bearerFormat="opaque",
    description="One device credential; cannot access operator endpoints.")


def _bearer(request):
    value = request.headers.get("authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token or " " in token or len(token) > 16384:
        raise HTTPException(401, "invalid_credentials", headers={"WWW-Authenticate": "Bearer"})
    return token


def operator_principal(request: Request,
    credential: Annotated[HTTPAuthorizationCredentials | None, Security(_operator_scheme)]):
    try:
        return request.app.state.operator_verifier.verify(_bearer(request))
    except OperatorAuthenticationError:
        raise HTTPException(401, "invalid_credentials", headers={"WWW-Authenticate": "Bearer"}) from None


def enrollment_principal(request: Request, session: SessionDependency,
    credential: Annotated[HTTPAuthorizationCredentials | None, Security(_enrollment_scheme)]):
    return authenticate_grant(session, _bearer(request))


def device_principal(request: Request, session: SessionDependency,
    credential: Annotated[HTTPAuthorizationCredentials | None, Security(_device_scheme)]):
    return authenticate_device(session, _bearer(request))
