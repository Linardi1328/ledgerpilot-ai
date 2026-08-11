from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError, get_request_id
from ledgerpilot.core.config import AuthMode, Settings
from ledgerpilot.identity.authorization import permissions_for_role
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.repositories.identity import IdentityRepository

DEV_SUBJECT_HEADER = "X-LedgerPilot-Dev-Subject"
DEV_FIRM_HEADER = "X-LedgerPilot-Firm"


class AuthenticationBackend(Protocol):
    def authenticate(self, *, request: Request, session: Session, settings: Settings) -> Principal:
        raise NotImplementedError


class DisabledAuthenticationBackend:
    def authenticate(self, *, request: Request, session: Session, settings: Settings) -> Principal:
        raise ApiError(
            status_code=401,
            code="unauthenticated",
            message="Authentication required.",
        )


class DevelopmentHeaderAuthenticationBackend:
    def authenticate(self, *, request: Request, session: Session, settings: Settings) -> Principal:
        if not settings.development_auth_is_enabled:
            raise ApiError(
                status_code=401,
                code="unauthenticated",
                message="Authentication required.",
            )

        external_subject = request.headers.get(DEV_SUBJECT_HEADER)
        firm_header = request.headers.get(DEV_FIRM_HEADER)
        if not external_subject or not firm_header:
            raise ApiError(
                status_code=401,
                code="unauthenticated",
                message="Authentication required.",
            )

        try:
            firm_id = UUID(firm_header)
        except ValueError as exc:
            raise ApiError(
                status_code=401,
                code="unauthenticated",
                message="Authentication required.",
            ) from exc

        repository = IdentityRepository(session)
        user = repository.get_active_user_by_subject(external_subject)
        if user is None:
            raise ApiError(
                status_code=401,
                code="unauthenticated",
                message="Authentication required.",
            )

        membership = repository.get_active_membership_for_firm(user_id=user.id, firm_id=firm_id)
        if membership is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

        try:
            role = Role(membership.role)
        except ValueError as exc:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.") from exc

        client_ids = repository.list_authorized_client_ids(
            membership_id=membership.id,
            firm_id=firm_id,
        )
        return Principal(
            user_id=user.id,
            firm_id=firm_id,
            membership_id=membership.id,
            role=role,
            authorized_client_ids=frozenset(client_ids),
            permissions=permissions_for_role(role),
            request_id=get_request_id(request),
        )


def get_authentication_backend(settings: Settings) -> AuthenticationBackend:
    if settings.auth_mode is AuthMode.DEVELOPMENT:
        return DevelopmentHeaderAuthenticationBackend()
    return DisabledAuthenticationBackend()
