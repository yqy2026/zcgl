"""One-off maintenance runner: backfill project entities from asset project_name.

背景：验收环境种子数据缺口 —— 19 个资产的 `project_name` 字段有值，
但 `projects` 表为空（资产接口 `project_id` 恒为 None），阻塞 G1 项目侧
验收与 REQ-PRJ 系列抽验（见 docs/issues/2026-08-09-mvp-g1-acceptance-dryrun.md §3.2）。

本脚本（幂等，可重复执行）：
1. 按 `assets.project_name` 去重建项目实体；
2. 项目创建走 `ProjectService.create_project`，保证 project_code 自动生成
   （`PRJ-{operator_seg}-{YYYYMM}-{SEQ4}`，需运营方 party 与 party.code 存在）；
3. 回填 `project_assets` 活跃关联（valid_to IS NULL），同一资产已有活跃关联则跳过。

运行：`cd backend && uv run --frozen --extra dev python scripts/maintenance/seed_projects_from_assets.py`
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from src.crud.project import project_crud
from src.database import async_session_scope
from src.models.asset import Asset
from src.models.project_asset import ProjectAsset
from src.schemas.project import ProjectCreate
from src.services.project.service import ProjectService

# 开发/验收环境唯一主体：广州国有资产管理集团有限公司（legal_entity / owner）
OWNER_PARTY_ID = "27ef9966-98f4-4a27-a221-978f744f9db7"
DEFAULT_PROJECT_STATUS = "active"


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def main() -> dict[str, object]:
    project_service = ProjectService()
    summary: dict[str, object] = {
        "project_names": 0,
        "projects_created": 0,
        "projects_existing": 0,
        "asset_links_created": 0,
        "asset_links_existing": 0,
        "detail": [],
    }

    async with async_session_scope() as db:
        # 1. 资产去重项目名
        rows = (await db.execute(select(Asset.project_name).distinct())).scalars().all()
        project_names = sorted(name for name in rows if name)
        summary["project_names"] = len(project_names)

        for name in project_names:
            # 2. 幂等：同名项目已存在则跳过创建
            existing = await project_crud.get_by_name(db, name)
            if existing is not None:
                project = existing
                summary["projects_existing"] += 1
            else:
                project = await project_service.create_project(
                    db,
                    obj_in=ProjectCreate(
                        project_name=name,
                        status=DEFAULT_PROJECT_STATUS,
                        manager_party_id=OWNER_PARTY_ID,
                    ),
                    created_by="maintenance-seed-projects",
                )
                summary["projects_created"] += 1

            # 3. 该项目名下的资产回填活跃关联
            asset_ids = (
                (
                    await db.execute(
                        select(Asset.id).where(Asset.project_name == name)
                    )
                )
                .scalars()
                .all()
            )
            linked = 0
            for asset_id in asset_ids:
                existing_link = (
                    await db.execute(
                        select(ProjectAsset.id).where(
                            ProjectAsset.asset_id == asset_id,
                            ProjectAsset.valid_to.is_(None),
                        )
                    )
                ).scalars().first()
                if existing_link is not None:
                    summary["asset_links_existing"] += 1
                    continue
                db.add(
                    ProjectAsset(
                        project_id=str(project.id),
                        asset_id=asset_id,
                        valid_from=_utcnow_naive(),
                        valid_to=None,
                    )
                )
                linked += 1
            summary["asset_links_created"] += linked
            summary["detail"].append(
                {
                    "project_name": name,
                    "project_code": project.project_code,
                    "assets": len(asset_ids),
                    "links_created": linked,
                }
            )

        # 显式提交，避免最后一个项目的关联依赖 scope 退出时的隐式提交
        await db.commit()

    return summary


if __name__ == "__main__":
    import json

    result = asyncio.run(main())
    print(json.dumps(result, ensure_ascii=False, indent=2))
