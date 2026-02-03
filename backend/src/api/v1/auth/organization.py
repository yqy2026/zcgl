"""
组织架构管理 API 路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ....core.exception_handler import BaseBusinessError, bad_request, not_found
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....crud.organization import organization as organization_crud
from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....models.organization import Organization, OrganizationHistory
from ....schemas.organization import (
    OrganizationBatchRequest,
    OrganizationCreate,
    OrganizationHistoryResponse,
    OrganizationMoveRequest,
    OrganizationResponse,
    OrganizationSearchRequest,
    OrganizationStatistics,
    OrganizationTree,
    OrganizationUpdate,
)
from ....services.organization import organization_service

router = APIRouter(tags=["组织架构管理"])


@router.get(
    "",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
@router.get(
    "/",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
async def get_organizations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """获取组织列表"""
    skip = (page - 1) * page_size
    organizations, total = await db.run_sync(
        lambda sync_db: organization_crud.get_multi_with_count(
            sync_db, skip=skip, limit=page_size
        )
    )
    items = [OrganizationResponse.model_validate(org) for org in organizations]
    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        message="获取组织列表成功",
    )


@router.get("/tree", response_model=list[OrganizationTree])
async def get_organization_tree(
    parent_id: str | None = Query(None, description="父组织ID，为空时获取根组织"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationTree]:
    """获取组织层级结构"""

    def _sync(sync_db: Session) -> list[OrganizationTree]:
        def build_tree(pid: str | None = None) -> list[OrganizationTree]:
            organizations = organization_crud.get_tree(sync_db, parent_id=pid)
            tree: list[OrganizationTree] = []
            for org in organizations:
                org_id = getattr(org, "id", "")
                children = build_tree(str(org_id))
                tree.append(
                    OrganizationTree(
                        id=str(getattr(org, "id", "")),
                        name=str(getattr(org, "name", "")),
                        level=int(getattr(org, "level", 0)),
                        sort_order=int(getattr(org, "sort_order", 0)),
                        children=children,
                    )
                )
            return tree

        return build_tree(parent_id)

    return await db.run_sync(_sync)


@router.get(
    "/search",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
async def search_organizations(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """搜索组织"""
    skip = (page - 1) * page_size
    organizations, total = await db.run_sync(
        lambda sync_db: organization_crud.get_multi_with_count(
            sync_db, keyword=keyword, skip=skip, limit=page_size
        )
    )
    items = [OrganizationResponse.model_validate(org) for org in organizations]

    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        message="搜索组织成功",
    )


@router.get("/statistics", response_model=OrganizationStatistics)
async def get_organization_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationStatistics:
    """获取组织统计信息"""
    stats = await db.run_sync(
        lambda sync_db: organization_service.get_statistics(sync_db)
    )
    return OrganizationStatistics(**stats)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationResponse:
    """根据ID获取组织详情"""
    organization = await db.run_sync(
        lambda sync_db: organization_crud.get(sync_db, id=org_id)
    )
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    return OrganizationResponse.model_validate(organization)


@router.get("/{org_id}/children", response_model=list[OrganizationResponse])
async def get_organization_children(
    org_id: str,
    is_recursive: bool = Query(False, description="是否递归获取子级组织"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """获取组织下的子级组织"""

    def _sync(sync_db: Session) -> tuple[Organization | None, list[Organization]]:
        parent = organization_crud.get(sync_db, id=org_id)
        if not parent:
            return None, []
        children = organization_crud.get_children(
            sync_db, parent_id=org_id, recursive=is_recursive
        )
        return parent, children

    parent, children = await db.run_sync(_sync)
    if not parent:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    return [OrganizationResponse.model_validate(org) for org in children]


@router.get("/{org_id}/path", response_model=list[OrganizationResponse])
async def get_organization_path(
    org_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """获取组织到根的路径"""

    def _sync(sync_db: Session) -> tuple[Organization | None, list[Organization]]:
        organization = organization_crud.get(sync_db, id=org_id)
        if not organization:
            return None, []
        path = organization_crud.get_path_to_root(sync_db, org_id=org_id)
        return organization, path

    organization, path = await db.run_sync(_sync)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    return [OrganizationResponse.model_validate(org) for org in path]


@router.get(
    "/{org_id}/history",
    response_model=APIResponse[PaginatedData[OrganizationHistoryResponse]],
)
async def get_organization_history(
    org_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """获取组织变更历史"""
    skip = (page - 1) * page_size

    def _sync(
        sync_db: Session,
    ) -> tuple[Organization | None, list[OrganizationHistory], int]:
        organization = organization_crud.get(sync_db, id=org_id)
        if not organization:
            return None, [], 0
        history, total = organization_service.get_history_with_count(
            sync_db, org_id=org_id, skip=skip, limit=page_size
        )
        return organization, history, total

    organization, history, total = await db.run_sync(_sync)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)

    items = [OrganizationHistoryResponse.model_validate(item) for item in history]

    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        message="获取组织历史成功",
    )


@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationResponse:
    """创建组织"""
    try:
        db_organization = await db.run_sync(
            lambda sync_db: organization_service.create_organization(
                sync_db, obj_in=organization
            )
        )
        return OrganizationResponse.model_validate(db_organization)
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    organization: OrganizationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationResponse:
    """更新组织"""
    try:
        db_organization = await db.run_sync(
            lambda sync_db: organization_service.update_organization(
                sync_db, org_id=org_id, obj_in=organization
            )
        )
        return OrganizationResponse.model_validate(db_organization)
    except BaseBusinessError:
        raise
    except ValueError as e:
        if str(e).startswith("组织ID"):
            raise not_found(str(e), resource_type="organization")
        raise bad_request(str(e))


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """删除组织（软删除）"""
    try:
        success = await db.run_sync(
            lambda sync_db: organization_service.delete_organization(
                sync_db, org_id=org_id, deleted_by=deleted_by
            )
        )
        if not success:
            raise not_found(
                "组织不存在", resource_type="organization", resource_id=org_id
            )
        return {"message": "组织删除成功"}
    except BaseBusinessError:
        raise
    except ValueError as e:
        raise bad_request(str(e))


@router.post("/{org_id}/move")
async def move_organization(
    org_id: str,
    move_request: OrganizationMoveRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """移动组织到新的父组织下"""
    try:
        update_dict: dict[str, Any] = {
            "parent_id": move_request.target_parent_id,
            "sort_order": move_request.sort_order,
            "updated_by": move_request.updated_by,
        }
        update_data = OrganizationUpdate.model_validate(update_dict)
        db_organization = await db.run_sync(
            lambda sync_db: organization_service.update_organization(
                sync_db, org_id=org_id, obj_in=update_data
            )
        )
        return {"message": "组织移动成功", "organization": db_organization}
    except BaseBusinessError:
        raise
    except ValueError as e:
        if str(e).startswith("组织ID"):
            raise not_found(str(e), resource_type="organization")
        raise bad_request(str(e))


@router.post("/batch")
async def batch_organization_operation(
    batch_request: OrganizationBatchRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """批量操作组织"""

    def _sync(sync_db: Session) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        results: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        for org_id in batch_request.organization_ids:
            try:
                if batch_request.action == "delete":
                    success = organization_service.delete_organization(
                        sync_db, org_id=org_id, deleted_by=batch_request.updated_by
                    )
                    if success:
                        results.append(
                            {"id": org_id, "status": "success", "message": "删除成功"}
                        )
                    else:
                        errors.append({"id": org_id, "error": "组织不存在"})
            except BaseBusinessError as e:
                errors.append({"id": org_id, "error": str(e)})
            except ValueError as e:
                errors.append({"id": org_id, "error": str(e)})
        return results, errors

    results, errors = await db.run_sync(_sync)

    return {
        "message": f"批量操作完成，成功 {len(results)} 个，失败 {len(errors)} 个",
        "results": results,
        "errors": errors,
    }


@router.post(
    "/advanced-search",
    response_model=APIResponse[PaginatedData[OrganizationResponse]],
)
async def advanced_search_organizations(
    search_request: OrganizationSearchRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """高级搜索组织"""

    def _sync(sync_db: Session) -> list[Organization]:
        if search_request.keyword:
            return organization_crud.search(
                sync_db,
                keyword=search_request.keyword,
                skip=search_request.skip,
                limit=search_request.page_size,
            )
        return organization_crud.get_multi_with_filters(
            sync_db, skip=search_request.skip, limit=search_request.page_size
        )

    organizations = await db.run_sync(_sync)

    if search_request.level:
        organizations = [
            org for org in organizations if org.level == search_request.level
        ]
    if search_request.parent_id:
        organizations = [
            org for org in organizations if org.parent_id == search_request.parent_id
        ]

    items = [OrganizationResponse.model_validate(org) for org in organizations]
    page_size = search_request.page_size
    page = (search_request.skip // page_size) + 1 if page_size > 0 else 1

    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=len(items),
        message="高级搜索组织成功",
    )
