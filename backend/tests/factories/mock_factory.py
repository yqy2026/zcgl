"""
Mock 对象工厂
提供统一的 Mock 对象创建方法，减少重复代码并提高测试一致性
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock


class MockFactory:
    """Mock 对象工厂"""

    @staticmethod
    def create_mock_user(
        user_id: str = "test_user_001", username: str = "testuser", role: str = "admin"
    ) -> MagicMock:
        """
        创建 Mock 用户对象

        Args:
            user_id: 用户 ID
            username: 用户名
            role: 用户角色

        Returns:
            Mock 用户对象
        """
        user = MagicMock()
        user.id = user_id
        user.username = username
        user.email = f"{username}@example.com"
        user.full_name = f"Test {username.capitalize()}"
        user.role = role
        user.is_active = True
        user.created_at = datetime.now()
        return user

    @staticmethod
    def create_mock_db() -> MagicMock:
        """
        创建 Mock 数据库会话

        Returns:
            配置好的 Mock 数据库会话
        """
        db = MagicMock()

        # Query 链式调用 Mock
        query = MagicMock()
        query.filter.return_value = query
        query.join.return_value = query
        query.outerjoin.return_value = query
        query.group_by.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.offset.return_value = query
        query.distinct.return_value = query
        query.all.return_value = []
        query.first.return_value = None
        query.count.return_value = 0
        query.with_entities.return_value = query

        db.query.return_value = query
        db.add = MagicMock()
        db.commit = MagicMock()
        db.flush = MagicMock()
        db.refresh = MagicMock()
        db.delete = MagicMock()
        db.rollback = MagicMock()
        db.execute = MagicMock()
        db.bulk_save_objects = MagicMock()
        db.expire = MagicMock()

        return db

    @staticmethod
    def create_mock_asset(
        asset_id: int = 1,
        name: str = "测试资产",
        code: str | None = None,
        area: float = 1000.0,
        location: str = "测试地点",
        status: str = "active",
    ) -> MagicMock:
        """
        创建 Mock 资产对象

        Args:
            asset_id: 资产 ID
            name: 资产名称
            code: 资产编码
            area: 面积
            location: 位置
            status: 状态

        Returns:
            Mock 资产对象
        """
        asset = MagicMock()
        asset.id = asset_id
        asset.name = name
        asset.code = code or f"ASSET-{str(asset_id).padStart(4, '0')}"
        asset.area = area
        asset.location = location
        asset.status = status
        asset.asset_type = "building"
        asset.created_at = datetime.now()
        asset.updated_at = datetime.now()
        return asset

    @staticmethod
    def create_mock_contract(
        contract_id: int = 1,
        contract_no: str | None = None,
        contract_name: str = "测试合同",
        contract_type: str = "lease",
        status: str = "active",
        total_rent: float = 100000.0,
    ) -> MagicMock:
        """
        创建 Mock 合同对象

        Args:
            contract_id: 合同 ID
            contract_no: 合同编号
            contract_name: 合同名称
            contract_type: 合同类型
            status: 状态
            total_rent: 总租金

        Returns:
            Mock 合同对象
        """
        contract = MagicMock()
        contract.id = contract_id
        contract.contract_no = (
            contract_no or f"HT-2024-{str(contract_id).padStart(3, '0')}"
        )
        contract.contract_name = contract_name
        contract.contract_type = contract_type
        contract.status = status
        contract.start_date = date(2024, 1, 1)
        contract.end_date = date(2024, 12, 31)
        contract.total_rent = Decimal(str(total_rent))
        contract.paid_amount = Decimal("0")
        contract.overdue_amount = Decimal("0")
        contract.tenant_name = f"测试租户 {contract_id}"
        contract.tenant_phone = "13800138000"
        contract.created_at = datetime.now()
        contract.updated_at = datetime.now()
        return contract

    @staticmethod
    def create_mock_ownership(
        ownership_id: int = 1,
        asset_id: int = 1,
        organization_name: str = "测试单位",
        ownership_ratio: float = 100.0,
    ) -> MagicMock:
        """
        创建 Mock 权属对象

        Args:
            ownership_id: 权属 ID
            asset_id: 资产 ID
            organization_name: 单位名称
            ownership_ratio: 权属比例

        Returns:
            Mock 权属对象
        """
        ownership = MagicMock()
        ownership.id = ownership_id
        ownership.asset_id = asset_id
        ownership.organization_id = ownership_id
        ownership.organization_name = organization_name
        ownership.ownership_ratio = Decimal(str(ownership_ratio))
        ownership.start_date = date(2024, 1, 1)
        ownership.is_active = True
        ownership.created_at = datetime.now()
        return ownership

    @staticmethod
    def create_mock_organization(
        organization_id: int = 1, name: str = "测试单位", code: str | None = None
    ) -> MagicMock:
        """
        创建 Mock 组织机构对象

        Args:
            organization_id: 组织 ID
            name: 组织名称
            code: 组织编码

        Returns:
            Mock 组织机构对象
        """
        org = MagicMock()
        org.id = organization_id
        org.name = name
        org.code = code or f"ORG-{str(organization_id).padStart(4, '0')}"
        org.type = "company"
        org.is_active = True
        org.created_at = datetime.now()
        return org

    @staticmethod
    def create_mock_response(
        data: Any = None, success: bool = True, message: str = "操作成功"
    ) -> dict:
        """
        创建标准的 API 响应对象

        Args:
            data: 响应数据
            success: 是否成功
            message: 响应消息

        Returns:
            标准响应字典
        """
        return {
            "success": success,
            "message": message,
            "data": data if data is not None else {},
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def create_mock_pagination_response(
        items: list[Any], total: int, page: int = 1, page_size: int = 10
    ) -> dict:
        """
        创建分页响应对象

        Args:
            items: 数据项列表
            total: 总数
            page: 当前页码
            page_size: 每页大小

        Returns:
            分页响应字典
        """
        total_pages = (total + page_size - 1) // page_size
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    @staticmethod
    def create_mock_query_result(
        data: list[Any], count: int | None = None
    ) -> MagicMock:
        """
        创建 Mock 查询结果

        Args:
            data: 数据列表
            count: 总数（如果为 None，则使用 len(data)）

        Returns:
            Mock 查询结果对象
        """
        result = MagicMock()
        result.all.return_value = data
        result.first.return_value = data[0] if data else None
        result.count.return_value = count if count is not None else len(data)
        return result
