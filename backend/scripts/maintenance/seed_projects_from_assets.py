"""One-off maintenance runner: backfill projects from asset project names.

The runner is idempotent: existing projects and current project-asset bindings
are reused. Project creation stays in ``ProjectService`` so generated project
codes follow the domain rules.

Usage:
    cd backend
    uv run --frozen --extra dev python scripts/maintenance/seed_projects_from_assets.py \
        --manager-party-id <party-uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import json
from uuid import UUID

from src.crud.project import project_crud
from src.crud.project_asset import project_asset_crud
from src.database import async_session_scope
from src.schemas.project import ProjectCreate
from src.services.project.service import ProjectService

DEFAULT_PROJECT_STATUS = "active"


def _party_id(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a valid UUID") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill projects and active bindings from asset project names."
    )
    parser.add_argument(
        "--manager-party-id",
        required=True,
        type=_party_id,
        help="Party UUID assigned as manager_party_id on newly created projects.",
    )
    return parser


async def main(*, manager_party_id: str) -> dict[str, object]:
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
        grouped_asset_ids = (
            await project_asset_crud.get_asset_ids_grouped_by_project_name(db)
        )
        summary["project_names"] = len(grouped_asset_ids)

        for name, asset_ids in grouped_asset_ids.items():
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
                        manager_party_id=manager_party_id,
                    ),
                    created_by="maintenance-seed-projects",
                    commit=False,
                )
                summary["projects_created"] += 1

            linked = 0
            for asset_id in asset_ids:
                existing_link = await project_asset_crud.get_active_by_asset_id(
                    db=db,
                    asset_id=asset_id,
                )
                if existing_link is not None:
                    summary["asset_links_existing"] += 1
                    continue
                await project_asset_crud.create_active(
                    db=db,
                    project_id=str(project.id),
                    asset_id=asset_id,
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

        await db.commit()

    return summary


if __name__ == "__main__":
    args = _build_parser().parse_args()
    result = asyncio.run(main(manager_party_id=args.manager_party_id))
    print(json.dumps(result, ensure_ascii=False, indent=2))
