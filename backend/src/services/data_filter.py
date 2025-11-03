from typing import Any
"""
数据过滤服务 - 方案B：前端优先简化
在API层面过滤掉前端不需要的字段，而不删除数据库字段
"""

import logging


logger = logging.getLogger(__name__)


class DataFilterService:
    """数据过滤服务"""

    # 前端不需要的字段列表
    REMOVED_FIELDS = {
        "annual_income",
        "annual_expense",
        "net_income",  # 财务字段
        "tenant_contact",  # 租户联系方式
        "last_audit_date",
        "audit_status",
        "auditor",  # 审核字段（保留audit_notes）
    }

    # 需要在API响应中移除的字段
    API_RESPONSE_FILTER_FIELDS = REMOVED_FIELDS.copy()

    @staticmethod
    def filter_asset_data(asset_data: dict[str, Any]) -> dict[str, Any]:
        """
        过滤资产数据，移除前端不需要的字段

        Args:
            asset_data: 原始资产数据

        Returns:
            过滤后的资产数据
        """
        if not isinstance(asset_data, dict):
            return asset_data

        # 创建过滤后的数据副本
        filtered_data = {}

        for key, value in asset_data.items():
            if key not in DataFilterService.API_RESPONSE_FILTER_FIELDS:
                filtered_data[key] = value
            else:
                logger.debug(f"过滤掉字段: {key}")

        return filtered_data

    @staticmethod
    def filter_asset_list(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        过滤资产列表

        Args:
            assets: 原始资产列表

        Returns:
            过滤后的资产列表
        """
        if not isinstance(assets, list):
            return assets

        return [DataFilterService.filter_asset_data(asset) for asset in assets]

    @staticmethod
    def filter_request_data(request_data: dict[str, Any]) -> dict[str, Any]:
        """
        过滤请求数据，移除不应该由客户端设置的字段

        Args:
            request_data: 客户端请求数据

        Returns:
            过滤后的请求数据
        """
        if not isinstance(request_data, dict):
            return request_data

        # 客户端不应该设置的字段
        client_forbidden_fields = {
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "version",
            "data_status",
        }

        filtered_data = {}

        for key, value in request_data.items():
            if key not in client_forbidden_fields:
                filtered_data[key] = value
            else:
                logger.debug(f"过滤掉客户端不应设置的字段: {key}")

        return filtered_data

    @staticmethod
    def sanitize_search_params(params: dict[str, Any]) -> dict[str, Any]:
        """
        清理搜索参数，移除无效的搜索字段

        Args:
            params: 原始搜索参数

        Returns:
            清理后的搜索参数
        """
        if not isinstance(params, dict):
            return params

        # 移除已删除字段的搜索条件
        invalid_search_fields = DataFilterService.REMOVED_FIELDS

        sanitized_params = {}

        for key, value in params.items():
            if key not in invalid_search_fields:
                sanitized_params[key] = value
            else:
                logger.debug(f"过滤掉无效搜索参数: {key}")

        return sanitized_params

    @staticmethod
    def get_field_mapping_info() -> dict[str, Any]:
        """
        获取字段映射信息

        Returns:
            字段映射信息
        """
        return {
            "removed_fields": list(DataFilterService.REMOVED_FIELDS),
            "retained_fields": {
                "basic": [
                    "id",
                    "ownership_entity",
                    "ownership_category",
                    "project_name",
                    "property_name",
                    "address",
                    "ownership_status",
                    "property_nature",
                    "usage_status",
                    "business_category",
                    "is_litigated",
                    "notes",
                ],
                "area": [
                    "land_area",
                    "actual_property_area",
                    "rentable_area",
                    "rented_area",
                    "unrented_area",
                    "non_commercial_area",
                    "occupancy_rate",
                    "include_in_occupancy_rate",
                ],
                "usage": ["certificated_usage", "actual_usage"],
                "tenant": ["tenant_name", "tenant_type"],
                "contract": [
                    "lease_contract_number",
                    "contract_start_date",
                    "contract_end_date",
                    "monthly_rent",
                    "deposit",
                    "is_sublease",
                    "sublease_notes",
                ],
                "management": ["manager_name", "business_model", "operation_status"],
                "operation": [
                    "operation_agreement_start_date",
                    "operation_agreement_end_date",
                    "operation_agreement_attachments",
                    "terminal_contract_files",
                ],
                "system": [
                    "data_status",
                    "created_by",
                    "updated_by",
                    "version",
                    "tags",
                ],
                "audit": [
                    "audit_notes"  # 只保留这一个审核字段
                ],
                "timestamps": ["created_at", "updated_at"],
                "relations": ["tenant_id", "project_id", "ownership_id"],
            },
            "calculated_fields": [
                "unrented_area",
                "occupancy_rate",  # 这些是计算字段，不存储在数据库
            ],
            "strategy": "frontend_priority",
            "description": "在API层面过滤字段，保持数据库结构不变",
        }
