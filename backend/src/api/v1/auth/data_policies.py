"""Role data-policy package configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import BaseBusinessError, internal_error
from ....database import get_async_db
from ....models.auth import User
from ....security.permissions import require_any_role
from ....services.authz import DataPolicyService, authz_event_bus

router = APIRouter(tags=["Data Policies"])


class RolePolicyUpdateRequest(BaseModel):
    policy_packages: list[str] = Field(
        default_factory=list,
        description="Policy package code list",
    )


@router.get("/roles/{role_id}/data-policies")
async def get_role_data_policies(
    role_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_any_role(["admin", "system_admin", "perm_admin"])),
) -> dict[str, object]:
    del current_user
    try:
        service = DataPolicyService(db, event_bus=authz_event_bus)
        return {
            "role_id": role_id,
            "policy_packages": await service.get_role_policy_packages(role_id),
        }
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error(
            "Failed to fetch role data policy packages.",
            original_error=exc,
        ) from exc


@router.put("/roles/{role_id}/data-policies")
async def put_role_data_policies(
    role_id: str,
    payload: RolePolicyUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_any_role(["admin", "system_admin", "perm_admin"])),
) -> dict[str, object]:
    del current_user
    try:
        service = DataPolicyService(db, event_bus=authz_event_bus)
        policy_packages = await service.set_role_policy_packages(
            role_id,
            policy_packages=payload.policy_packages,
        )
        return {
            "role_id": role_id,
            "policy_packages": policy_packages,
        }
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error(
            "Failed to update role data policy packages.",
            original_error=exc,
        ) from exc


@router.get("/data-policies/templates")
async def get_data_policy_templates(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_any_role(["admin", "system_admin", "perm_admin"])),
) -> dict[str, dict[str, str]]:
    del current_user
    service = DataPolicyService(db, event_bus=authz_event_bus)
    return service.list_templates()
