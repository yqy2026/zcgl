"""
联系人管理 API 端点
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...crud.contact import contact_crud
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
    PrimaryContactResponse,
)

router = APIRouter()


@router.post("/", response_model=ContactResponse, summary="创建联系人")
def create_contact(
    *,
    db: Session = Depends(get_db),
    contact_in: ContactCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    创建新的联系人

    - 如果 is_primary=True，会自动取消该实体的其他主要联系人
    - 支持权属方(ownership)、项目(project)、租户(tenant)等实体类型
    """
    # Create a copy with the user info
    contact_data = contact_in.model_dump()
    contact_data["created_by"] = current_user.username
    contact_data["updated_by"] = current_user.username

    try:
        contact = contact_crud.create(db=db, obj_in=contact_data)
        return contact
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建联系人失败: {str(e)}")


@router.get("/{contact_id}", response_model=ContactResponse, summary="获取联系人详情")
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取联系人详情"""
    contact = contact_crud.get(db, id=contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return contact


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=ContactListResponse,
    summary="获取实体的所有联系人",
)
def get_entity_contacts(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
) -> Any:
    """
    获取指定实体的所有联系人

    - entity_type: 实体类型 (ownership/project/tenant)
    - entity_id: 实体ID
    - 返回结果按主要联系人优先，然后按创建时间倒序
    """
    skip = (page - 1) * limit
    contacts, total = contact_crud.get_multi(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=limit,
    )

    pages = (total + limit - 1) // limit

    return ContactListResponse(
        items=list(contacts), total=total, page=page, limit=limit, pages=pages
    )


@router.get(
    "/entity/{entity_type}/{entity_id}/primary",
    response_model=PrimaryContactResponse,
    summary="获取实体的主要联系人",
)
def get_primary_contact(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取指定实体的主要联系人

    - entity_type: 实体类型 (ownership/project/tenant)
    - entity_id: 实体ID
    - 如果没有主要联系人，返回404
    """
    contact = contact_crud.get_primary(
        db=db, entity_type=entity_type, entity_id=entity_id
    )
    if not contact:
        raise HTTPException(status_code=404, detail="主要联系人不存在")

    return PrimaryContactResponse.model_validate(contact)


@router.put("/{contact_id}", response_model=ContactResponse, summary="更新联系人")
def update_contact(
    contact_id: str,
    *,
    db: Session = Depends(get_db),
    contact_in: ContactUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """更新联系人信息"""
    contact = contact_crud.get(db, id=contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")

    # Include updated_by in the update
    update_data = contact_in.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user.username

    try:
        updated_contact = contact_crud.update(
            db=db, db_obj=contact, obj_in=update_data
        )
        return updated_contact
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新联系人失败: {str(e)}")


@router.delete("/{contact_id}", response_model=ContactResponse, summary="删除联系人")
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    删除联系人（软删除）

    - 设置 is_active=False
    - 数据保留在数据库中
    """
    contact = contact_crud.delete(db, id=contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return contact


@router.post(
    "/batch/{entity_type}/{entity_id}",
    response_model=list[ContactResponse],
    summary="批量创建联系人",
)
def create_contacts_batch(
    entity_type: str,
    entity_id: str,
    *,
    db: Session = Depends(get_db),
    contacts_in: list[ContactCreate],
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    批量创建联系人

    - 支持一次创建多个联系人
    - 自动设置创建人信息
    """
    created_contacts = []
    for contact_in in contacts_in:
        # Create a dict with all required fields
        contact_data = contact_in.model_dump()
        contact_data["entity_type"] = entity_type
        contact_data["entity_id"] = entity_id
        contact_data["created_by"] = current_user.username
        contact_data["updated_by"] = current_user.username

        try:
            contact = contact_crud.create(db=db, obj_in=contact_data)
            created_contacts.append(contact)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"批量创建失败: {str(e)}")

    return created_contacts
