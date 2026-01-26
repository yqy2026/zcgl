"""
组织架构管理API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....core.exception_handler import bad_request, not_found
from ....crud.organization import organization as organization_crud
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
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


@router.get("", response_model=list[OrganizationResponse])
@router.get("/", response_model=list[OrganizationResponse])
async def get_organizations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """获取组织列表"""
    # FastAPI will convert Organization to OrganizationResponse via response_model
    skip = (page - 1) * page_size
    organizations = organization_crud.get_multi_with_filters(
        db, skip=skip, limit=page_size
    )
    return [OrganizationResponse.model_validate(org) for org in organizations]


@router.get("/tree", response_model=list[OrganizationTree])
async def get_organization_tree(
    parent_id: str | None = Query(None, description="父组织ID，为空则获取根组织"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationTree]:
    """获取组织树形结构"""

    def build_tree(pid: str | None = None) -> list[OrganizationTree]:
        """递归构建组织树"""
        organizations = organization_crud.get_tree(db, parent_id=pid)
        tree = []

        for org in organizations:
            # Access attribute values to avoid Column type issues
            org_id = getattr(org, "id", "")
            children = build_tree(org_id)
            tree_node = OrganizationTree(
                id=str(getattr(org, "id", "")),
                name=str(getattr(org, "name", "")),
                level=int(getattr(org, "level", 0)),
                sort_order=int(getattr(org, "sort_order", 0)),
                children=children,
            )
            tree.append(tree_node)

        return tree

    return build_tree(parent_id)


@router.get("/search", response_model=list[OrganizationResponse])
async def search_organizations(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """搜索组织"""
    # FastAPI will convert Organization to OrganizationResponse via response_model
    skip = (page - 1) * page_size
    organizations = organization_crud.search(
        db, keyword=keyword, skip=skip, limit=page_size
    )
    return [OrganizationResponse.model_validate(org) for org in organizations]


@router.get("/statistics", response_model=OrganizationStatistics)
async def get_organization_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationStatistics:
    """获取组织统计信息"""
    stats = organization_service.get_statistics(db)
    return OrganizationStatistics(**stats)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationResponse:
    """根据ID获取组织详情"""
    from ....models.organization import Organization

    organization: Organization | None = organization_crud.get(db, id=org_id)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)
    return OrganizationResponse.model_validate(organization)


@router.get("/{org_id}/children", response_model=list[OrganizationResponse])
async def get_organization_children(
    org_id: str,
    is_recursive: bool = Query(False, description="是否递归获取所有子组织"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """获取组织的子组织"""
    # 先检查父组织是否存在
    parent = organization_crud.get(db, id=org_id)
    if not parent:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)

    children = organization_crud.get_children(
        db, parent_id=org_id, recursive=is_recursive
    )
    return [OrganizationResponse.model_validate(org) for org in children]


@router.get("/{org_id}/path", response_model=list[OrganizationResponse])
async def get_organization_path(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """获取组织到根节点的路径"""
    # 检查组织是否存在
    organization = organization_crud.get(db, id=org_id)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)

    path = organization_crud.get_path_to_root(db, org_id=org_id)
    return [OrganizationResponse.model_validate(org) for org in path]


@router.get("/{org_id}/history", response_model=list[OrganizationHistoryResponse])
async def get_organization_history(
    org_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationHistoryResponse]:
    """获取组织变更历史"""
    # 检查组织是否存在
    organization = organization_crud.get(db, id=org_id)
    if not organization:
        raise not_found("组织不存在", resource_type="organization", resource_id=org_id)

    skip = (page - 1) * page_size
    history = organization_service.get_history(
        db, org_id=org_id, skip=skip, limit=page_size
    )
    return [OrganizationHistoryResponse.model_validate(item) for item in history]


@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    organization: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationResponse:
    """创建组织"""
    try:
        db_organization = organization_service.create_organization(
            db, obj_in=organization
        )
        return OrganizationResponse.model_validate(db_organization)
    except ValueError as e:
        raise bad_request(str(e))


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    organization: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationResponse:
    """更新组织"""
    try:
        db_organization = organization_service.update_organization(
            db, org_id=org_id, obj_in=organization
        )
        return OrganizationResponse.model_validate(db_organization)
    except ValueError as e:
        if str(e).startswith("组织ID"):
            raise not_found(str(e), resource_type="organization")
        raise bad_request(str(e))


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """删除组织（软删除）"""
    try:
        success = organization_service.delete_organization(
            db, org_id=org_id, deleted_by=deleted_by
        )
        if not success:
            raise not_found(
                "组织不存在", resource_type="organization", resource_id=org_id
            )
        return {"message": "组织删除成功"}
    except ValueError as e:
        raise bad_request(str(e))


@router.post("/{org_id}/move")
async def move_organization(
    org_id: str,
    move_request: OrganizationMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """移动组织到新的父组织下"""
    try:
        # Create update data as dict to avoid field requirements
        update_dict: dict[str, Any] = {
            "parent_id": move_request.target_parent_id,
            "sort_order": move_request.sort_order,
            "updated_by": move_request.updated_by,
        }
        # Create OrganizationUpdate with model_validate
        update_data = OrganizationUpdate.model_validate(update_dict)
        db_organization = organization_service.update_organization(
            db, org_id=org_id, obj_in=update_data
        )
        return {"message": "组织移动成功", "organization": db_organization}
    except ValueError as e:
        if str(e).startswith("组织ID"):
            raise not_found(str(e), resource_type="organization")
        raise bad_request(str(e))


@router.post("/batch")
async def batch_organization_operation(
    batch_request: OrganizationBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """批量操作组织"""
    results: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for org_id in batch_request.organization_ids:
        try:
            if batch_request.action == "delete":
                success = organization_service.delete_organization(
                    db, org_id=org_id, deleted_by=batch_request.updated_by
                )
                if success:
                    results.append(
                        {"id": org_id, "status": "success", "message": "删除成功"}
                    )
                else:
                    errors.append({"id": org_id, "error": "组织不存在"})

        except ValueError as e:
            errors.append({"id": org_id, "error": str(e)})

    return {
        "message": f"批量操作完成，成功 {len(results)} 个，失败 {len(errors)} 个",
        "results": results,
        "errors": errors,
    }


@router.post("/advanced-search", response_model=list[OrganizationResponse])
async def advanced_search_organizations(
    search_request: OrganizationSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """高级搜索组织"""
    # FastAPI will convert Organization to OrganizationResponse via response_model
    if search_request.keyword:
        organizations = organization_crud.search(
            db,
            keyword=search_request.keyword,
            skip=search_request.skip,
            limit=search_request.page_size,
        )
    else:
        organizations = organization_crud.get_multi_with_filters(
            db, skip=search_request.skip, limit=search_request.page_size
        )

    # 内存中过滤其他条件，保持原有逻辑
    if search_request.level:
        organizations = [
            org for org in organizations if org.level == search_request.level
        ]
    if search_request.parent_id:
        organizations = [
            org for org in organizations if org.parent_id == search_request.parent_id
        ]

    return [OrganizationResponse.model_validate(org) for org in organizations]
