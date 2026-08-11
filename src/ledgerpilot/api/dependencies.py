from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from ledgerpilot.api.errors import ApiError
from ledgerpilot.core.config import Settings
from ledgerpilot.identity.authentication import AuthenticationBackend
from ledgerpilot.identity.authorization import has_permission
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_session(request: Request) -> Generator[Session]:
    session_factory = cast(sessionmaker[Session], request.app.state.session_factory)
    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_principal(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_session)],
) -> Principal:
    backend = cast(AuthenticationBackend, request.app.state.auth_backend)
    return backend.authenticate(request=request, session=session, settings=settings)


def require_permission(permission: Permission) -> Callable[[Principal], Principal]:
    def dependency(principal: Annotated[Principal, Depends(get_current_principal)]) -> Principal:
        if not has_permission(principal, permission):
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")
        return principal

    return dependency
