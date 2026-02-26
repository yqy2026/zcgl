"""Role data-policy package service backed by ABAC policy tables."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import InvalidRequestError, ResourceNotFoundError
from ...models.abac import ABACPolicy, ABACRolePolicy
from ...models.rbac import Role
from .events import AUTHZ_ROLE_POLICY_UPDATED, AuthzEventBus

DATA_POLICY_TEMPLATES: dict[str, dict[str, str]] = {
    "platform_admin": {
        "policy_name": "platform_admin",
        "name": "平台管理员",
        "description": "全量访问",
    },
    "asset_owner_operator": {
        "policy_name": "asset_owner_operator",
        "name": "产权方运营",
        "description": "产权维度读写",
    },
    "asset_manager_operator": {
        "policy_name": "asset_manager_operator",
        "name": "经营方运营",
        "description": "经营维度读写",
    },
    "dual_party_viewer": {
        "policy_name": "dual_party_viewer",
        "name": "双维度只读",
        "description": "产权+经营只读",
    },
    "project_manager_operator": {
        "policy_name": "project_manager_operator",
        "name": "项目运营",
        "description": "项目维度读写",
    },
    "audit_viewer": {
        "policy_name": "audit_viewer",
        "name": "审计只读",
        "description": "审计视角访问",
    },
    "no_data_access": {
        "policy_name": "no_data_access",
        "name": "无数据访问",
        "description": "仅功能访问，无数据读写",
    },
}

_TEMPLATE_ORDER = list(DATA_POLICY_TEMPLATES.keys())
_POLICY_NAME_TO_PACKAGE = {
    spec["policy_name"]: code for code, spec in DATA_POLICY_TEMPLATES.items()
}


class DataPolicyService:
    """Manage role to data-policy package bindings."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        event_bus: AuthzEventBus | None = None,
    ) -> None:
        self.db = db
        self.event_bus = event_bus

    def list_templates(self) -> dict[str, dict[str, str]]:
        templates: dict[str, dict[str, str]] = {}
        for code, spec in DATA_POLICY_TEMPLATES.items():
            templates[code] = {
                "name": spec["name"],
                "description": spec["description"],
            }
        return templates

    async def get_role_policy_packages(self, role_id: str) -> list[str]:
        await self._ensure_role_exists(role_id)

        stmt = (
            select(ABACPolicy.name)
            .join(ABACRolePolicy, ABACRolePolicy.policy_id == ABACPolicy.id)
            .where(
                ABACRolePolicy.role_id == role_id,
                ABACRolePolicy.enabled.is_(True),
                ABACPolicy.enabled.is_(True),
            )
        )
        policy_names = [row[0] for row in (await self.db.execute(stmt)).all()]
        return self._packages_from_policy_names(policy_names)

    async def set_role_policy_packages(
        self,
        role_id: str,
        *,
        policy_packages: list[str],
    ) -> list[str]:
        await self._ensure_role_exists(role_id)

        normalized_packages = self._normalize_package_codes(policy_packages)
        template_policies = await self._load_template_policies(normalized_packages)

        template_policy_names = {
            spec["policy_name"] for spec in DATA_POLICY_TEMPLATES.values()
        }
        template_policy_rows = await self.db.execute(
            select(ABACPolicy.id).where(ABACPolicy.name.in_(template_policy_names))
        )
        template_policy_ids = [str(row[0]) for row in template_policy_rows.all()]

        if template_policy_ids:
            await self.db.execute(
                delete(ABACRolePolicy).where(
                    ABACRolePolicy.role_id == role_id,
                    ABACRolePolicy.policy_id.in_(template_policy_ids),
                )
            )

        for package_code in normalized_packages:
            policy = template_policies[package_code]
            self.db.add(
                ABACRolePolicy(
                    role_id=role_id,
                    policy_id=str(policy.id),
                    enabled=True,
                )
            )

        await self.db.commit()
        await self._publish_role_policy_event(role_id, normalized_packages)
        return normalized_packages

    async def _ensure_role_exists(self, role_id: str) -> None:
        role_row = await self.db.execute(select(Role.id).where(Role.id == role_id))
        if role_row.scalar_one_or_none() is None:
            raise ResourceNotFoundError("角色", role_id)

    def _normalize_package_codes(self, package_codes: Iterable[str]) -> list[str]:
        normalized: list[str] = []
        for raw_code in package_codes:
            code = str(raw_code).strip()
            if code == "":
                continue
            if code not in DATA_POLICY_TEMPLATES:
                raise InvalidRequestError(
                    "包含未知数据策略包编码",
                    field="policy_packages",
                    details={"invalid_code": code},
                )
            if code not in normalized:
                normalized.append(code)
        return normalized

    async def _load_template_policies(
        self,
        package_codes: list[str],
    ) -> dict[str, ABACPolicy]:
        if not package_codes:
            return {}

        expected_policy_names = [
            DATA_POLICY_TEMPLATES[code]["policy_name"] for code in package_codes
        ]
        stmt = select(ABACPolicy).where(ABACPolicy.name.in_(expected_policy_names))
        rows = (await self.db.execute(stmt)).scalars().all()
        by_name = {str(policy.name): policy for policy in rows}

        missing_names = sorted(
            [name for name in expected_policy_names if name not in by_name]
        )
        if missing_names:
            raise InvalidRequestError(
                "策略包模板缺失，请先执行 ABAC seed 迁移",
                field="policy_packages",
                details={"missing_policies": missing_names},
            )

        return {
            code: by_name[DATA_POLICY_TEMPLATES[code]["policy_name"]]
            for code in package_codes
        }

    @staticmethod
    def _packages_from_policy_names(policy_names: list[str]) -> list[str]:
        resolved: set[str] = set()
        for policy_name in policy_names:
            package_code = _POLICY_NAME_TO_PACKAGE.get(str(policy_name))
            if package_code is not None:
                resolved.add(package_code)

        return [code for code in _TEMPLATE_ORDER if code in resolved]

    async def _publish_role_policy_event(
        self,
        role_id: str,
        policy_packages: list[str],
    ) -> None:
        if self.event_bus is None:
            return

        self.event_bus.publish_invalidation(
            event_type=AUTHZ_ROLE_POLICY_UPDATED,
            payload={
                "role_id": role_id,
                "policy_packages": list(policy_packages),
            },
        )


__all__ = [
    "DATA_POLICY_TEMPLATES",
    "DataPolicyService",
]
