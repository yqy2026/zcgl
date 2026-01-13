"""
组织架构管理API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...crud.organization import organization as organization_crud
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...schemas.organization import (
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
from ...services.organization import organization_service

router = APIRouter(tags=["组织架构管理"])


@router.get("", response_model=list[OrganizationResponse])
@router.get("/", response_model=list[OrganizationResponse])
async def get_organizations(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """获取组织列表"""
    # FastAPI will convert Organization to OrganizationResponse via response_model
    organizations = organization_crud.get_multi_with_filters(db, skip=skip, limit=limit)
    return organizations  # type: ignore[return-value]


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
            org_id = getattr(org, 'id', '')
            children = build_tree(org_id)
            tree_node = OrganizationTree(
                id=str(getattr(org, 'id', '')),
                name=str(getattr(org, 'name', '')),
                level=int(getattr(org, 'level', 0)),
                sort_order=int(getattr(org, 'sort_order', 0)),
                children=children,
            )
            tree.append(tree_node)

        return tree

    return build_tree(parent_id)


@router.get("/search", response_model=list[OrganizationResponse])
async def search_organizations(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """搜索组织"""
    # FastAPI will convert Organization to OrganizationResponse via response_model
    organizations = organization_crud.search(db, keyword=keyword, skip=skip, limit=limit)
    return organizations  # type: ignore[return-value]


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
    organization = organization_crud.get(db, id=org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="组织不存在")
    return organization


@router.get("/{org_id}/children", response_model=list[OrganizationResponse])
async def get_organization_children(
    org_id: str,
    recursive: bool = Query(False, description="是否递归获取所有子组织"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationResponse]:
    """获取组织的子组织"""
    # 先检查父组织是否存在
    parent = organization_crud.get(db, id=org_id)
    if not parent:
        raise HTTPException(status_code=404, detail="组织不存在")

    children = organization_crud.get_children(db, parent_id=org_id, recursive=recursive)
    return children


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
        raise HTTPException(status_code=404, detail="组织不存在")

    path = organization_crud.get_path_to_root(db, org_id=org_id)
    return path


@router.get("/{org_id}/history", response_model=list[OrganizationHistoryResponse])
async def get_organization_history(
    org_id: str,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationHistoryResponse]:
    """获取组织变更历史"""
    # 检查组织是否存在
    organization = organization_crud.get(db, id=org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="组织不存在")

    history = organization_service.get_history(
        db, org_id=org_id, skip=skip, limit=limit
    )
    return history


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
        return db_organization
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        return db_organization
    except ValueError as e:
        if str(e).startswith("组织ID"):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


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
            raise HTTPException(status_code=404, detail="组织不存在")
        return {"message": "组织删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
async def batch_organization_operation(
    batch_request: OrganizationBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """批量操作组织"""
    results = []
    errors = []

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
            limit=search_request.limit,
        )
    else:
        organizations = organization_crud.get_multi_with_filters(
            db, skip=search_request.skip, limit=search_request.limit
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

    return organizations  # type: ignore[return-value]
