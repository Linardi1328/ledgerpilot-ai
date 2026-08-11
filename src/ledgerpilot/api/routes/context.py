from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ledgerpilot.api.dependencies import require_permission
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal

router = APIRouter()


@router.get("/context")
def context(
    principal: Annotated[Principal, Depends(require_permission(Permission.VIEW_CONTEXT))],
) -> dict[str, Any]:
    return {
        "user_id": str(principal.user_id),
        "firm_id": str(principal.firm_id),
        "membership_id": str(principal.membership_id),
        "role": principal.role.value,
        "permissions": sorted(permission.value for permission in principal.permissions),
        "authorized_client_ids": sorted(
            str(client_id) for client_id in principal.authorized_client_ids
        ),
    }
