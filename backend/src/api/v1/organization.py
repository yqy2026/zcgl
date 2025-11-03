"""
组织架构管理API路由
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...crud.organization import get_organization_crud
from ...database import get_db
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

router = APIRouter(tags=["组织架构管理"])


@router.get("/", response_model=list[OrganizationResponse])
async def get_organizations(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db),
):
    """获取组织列表"""
    crud = get_organization_crud(db)
    organizations = crud.get_all(skip=skip, limit=limit)
    return organizations


@router.get("/tree", response_model=list[OrganizationTree])
async def get_organization_tree(
    parent_id: str | None = Query(None, description="父组织ID，为空则获取根组织"),
    db: Session = Depends(get_db),
):
    """获取组织树形结构"""
    crud = get_organization_crud(db)

    def build_tree(parent_id: str | None = None) -> list[OrganizationTree]:
        """递归构建组织树"""
        organizations = crud.get_tree(parent_id)
        tree = []

        for org in organizations:
            children = build_tree(org.id)
            tree_node = OrganizationTree(
                id=org.id,
                name=org.name,
                level=org.level,
                sort_order=org.sort_order,
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
):
    """搜索组织"""
    crud = get_organization_crud(db)
    organizations = crud.search(keyword, skip=skip, limit=limit)
    return organizations


@router.get("/statistics", response_model=OrganizationStatistics)
async def get_organization_statistics(db: Session = Depends(get_db)):
    """获取组织统计信息"""
    crud = get_organization_crud(db)
    stats = crud.get_statistics()
    return OrganizationStatistics(**stats)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: str, db: Session = Depends(get_db)):
    """根据ID获取组织详情"""
    crud = get_organization_crud(db)
    organization = crud.get(org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="组织不存在")
    return organization


@router.get("/{org_id}/children", response_model=list[OrganizationResponse])
async def get_organization_children(
    org_id: str,
    recursive: bool = Query(False, description="是否递归获取所有子组织"),
    db: Session = Depends(get_db),
):
    """获取组织的子组织"""
    crud = get_organization_crud(db)

    # 先检查父组织是否存在
    parent = crud.get(org_id)
    if not parent:
        raise HTTPException(status_code=404, detail="组织不存在")

    children = crud.get_children(org_id, recursive=recursive)
    return children


@router.get("/{org_id}/path", response_model=list[OrganizationResponse])
async def get_organization_path(org_id: str, db: Session = Depends(get_db)):
    """获取组织到根节点的路径"""
    crud = get_organization_crud(db)

    # 检查组织是否存在
    organization = crud.get(org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="组织不存在")

    path = crud.get_path_to_root(org_id)
    return path


@router.get("/{org_id}/history", response_model=list[OrganizationHistoryResponse])
async def get_organization_history(
    org_id: str,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db),
):
    """获取组织变更历史"""
    crud = get_organization_crud(db)

    # 检查组织是否存在
    organization = crud.get(org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="组织不存在")

    history = crud.get_history(org_id, skip=skip, limit=limit)
    return history


@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    organization: OrganizationCreate, db: Session = Depends(get_db)
):
    """创建组织"""
    crud = get_organization_crud(db)

    try:
        db_organization = crud.create(organization)
        return db_organization
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str, organization: OrganizationUpdate, db: Session = Depends(get_db)
):
    """更新组织"""
    crud = get_organization_crud(db)

    try:
        db_organization = crud.update(org_id, organization)
        if not db_organization:
            raise HTTPException(status_code=404, detail="组织不存在")
        return db_organization
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: Session = Depends(get_db),
):
    """删除组织（软删除）"""
    crud = get_organization_crud(db)

    try:
        success = crud.delete(org_id, deleted_by=deleted_by)
        if not success:
            raise HTTPException(status_code=404, detail="组织不存在")
        return {"message": "组织删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/move")
async def move_organization(
    org_id: str, move_request: OrganizationMoveRequest, db: Session = Depends(get_db)
):
    """移动组织到新的父组织下"""
    crud = get_organization_crud(db)

    try:
        update_data = OrganizationUpdate(
            parent_id=move_request.target_parent_id,
            sort_order=move_request.sort_order,
            updated_by=move_request.updated_by,
        )
        db_organization = crud.update(org_id, update_data)
        if not db_organization:
            raise HTTPException(status_code=404, detail="组织不存在")
        return {"message": "组织移动成功", "organization": db_organization}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
async def batch_organization_operation(
    batch_request: OrganizationBatchRequest, db: Session = Depends(get_db)
):
    """批量操作组织"""
    crud = get_organization_crud(db)
    results = []
    errors = []

    for org_id in batch_request.organization_ids:
        try:
            if batch_request.action == "delete":
                success = crud.delete(org_id, deleted_by=batch_request.updated_by)
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
    search_request: OrganizationSearchRequest, db: Session = Depends(get_db)
):
    """高级搜索组织"""
    crud = get_organization_crud(db)

    if search_request.keyword:
        organizations = crud.search(
            search_request.keyword, search_request.skip, search_request.limit
        )
    else:
        organizations = crud.get_all(search_request.skip, search_request.limit)

    # 根据其他条件过滤
    if search_request.level:
        organizations = [
            org for org in organizations if org.level == search_request.level
        ]
    if search_request.parent_id:
        organizations = [
            org for org in organizations if org.parent_id == search_request.parent_id
        ]

    return organizations
