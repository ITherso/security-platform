"""Independent inventory API. It never imports endpoint enforcement modules."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from security_platform.auth.operator_oidc import OperatorVerifier
from security_platform.boundary import RequestBoundary
from security_platform.db import Database
from security_platform.services.common import EventCursorConflict, ServiceError, ServiceLimits
from security_platform.settings import Settings
from security_platform.api import device, operator


def validate_runtime_role(database):
    with database.session() as session:
        role = session.execute(text("SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
        # Own flags alone miss an apparently unprivileged role that inherits
        # an owner role, or can SET ROLE into it. Both bypass table privileges.
        owner_access = session.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' "
            "AND pg_has_role(current_user, tableowner, 'MEMBER'))"))
        can_create = session.scalar(text("SELECT has_schema_privilege(current_user, 'public', 'CREATE') "
            "OR has_database_privilege(current_user, current_database(), 'CREATE')"))
        if any(role) or owner_access or can_create:
            raise ValueError("The API requires a separate unprivileged runtime database role")
        session.execute(text("SELECT 1 FROM alembic_version"))


def create_app(settings=None):
    settings = Settings.from_environment() if settings is None else settings
    verifier = OperatorVerifier(issuer=settings.operator_issuer, audience=settings.operator_audience, jwks_file=settings.jwks_file)
    database = Database(settings.database_url)
    limits = ServiceLimits(max_devices=settings.max_devices_per_tenant,
        max_active_grants=settings.max_active_grants_per_tenant, max_grant_records=settings.max_active_grants_per_tenant * 2,
        max_audits=settings.max_audit_events_per_tenant, stale_seconds=settings.stale_after_seconds,
        grant_ttl_seconds=settings.enrollment_ttl_seconds, max_grant_ttl_seconds=settings.max_enrollment_ttl_seconds,
        credential_ttl_seconds=settings.credential_ttl_seconds, max_events_per_device=settings.max_events_per_device,
        max_open_alerts_per_device=settings.max_open_alerts_per_device)

    @asynccontextmanager
    async def lifespan(app):
        try:
            validate_runtime_role(database)
            yield
        finally:
            database.close()

    app = FastAPI(title="Security Platform inventory API", version="0.1.0", docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings, app.state.database = settings, database
    app.state.operator_verifier, app.state.limits = verifier, limits

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        body = {"detail": str(exc)[:160]}
        if isinstance(exc, EventCursorConflict):
            # Only event ingestion raises it; every other route keeps {"detail"}.
            body.update(last_batch_sequence=exc.last_batch_sequence, last_event_seq=exc.last_event_seq)
        return JSONResponse(body, status_code=exc.status_code,
            headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else {})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse({"detail": "database_unavailable"}, status_code=503)

    @app.get("/livez", tags=["operations"])
    def live():
        return {"status": "alive"}

    @app.get("/readyz", tags=["operations"])
    def ready():
        try:
            with database.session() as session:
                session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except SQLAlchemyError:
            return JSONResponse({"status": "unavailable"}, status_code=503)

    app.include_router(operator.router)
    app.include_router(device.router)
    app.add_middleware(RequestBoundary, settings=settings)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
    return app
