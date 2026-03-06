"""
资产生命周期集成测试

Integration tests for complete asset lifecycle
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.crud.asset_support import SensitiveDataHandler
from src.models.enum_field import EnumFieldType, EnumFieldValue
from src.models.ownership import Ownership
from src.services.organization_permission_service import (
    invalidate_user_accessible_organizations_cache,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """通过真实登录流程注入认证 cookie。"""
    admin_user = test_data["admin"]
    invalidate_user_accessible_organizations_cache(str(admin_user.id))
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200

    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    """返回 cookie-only 场景写操作所需 CSRF 头。"""
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


class TestAssetLifecycle:
    """资产核心生命周期契约测试。"""

    @staticmethod
    def _ensure_asset_enum_data(db_session) -> None:
        enum_defs: dict[str, tuple[str, list[str]]] = {
            "ownership_status": ("确权状态", ["已确权", "部分确权", "未确权", "其它"]),
            "property_nature": ("物业性质", ["经营类", "公房", "自用", "其它"]),
            "usage_status": (
                "使用状态",
                ["出租", "闲置", "自用", "公房（出租）", "公房（闲置）", "其它"],
            ),
            "data_status": ("数据状态", ["正常", "已删除", "已归档"]),
        }

        for code, (name, values) in enum_defs.items():
            enum_type = (
                db_session.query(EnumFieldType)
                .filter(EnumFieldType.code == code)
                .first()
            )
            if enum_type is None:
                enum_type = EnumFieldType(
                    name=name,
                    code=code,
                    category="资产管理",
                    is_system=True,
                    status="active",
                    is_deleted=False,
                    created_by="integration_test",
                    updated_by="integration_test",
                )
                db_session.add(enum_type)
                db_session.flush()
            else:
                enum_type.status = "active"
                enum_type.is_deleted = False
                enum_type.updated_by = "integration_test"

            existing_values = {
                value_obj.value: value_obj
                for value_obj in db_session.query(EnumFieldValue)
                .filter(EnumFieldValue.enum_type_id == enum_type.id)
                .all()
            }

            for sort_order, value in enumerate(values, start=1):
                value_obj = existing_values.get(value)
                if value_obj is None:
                    db_session.add(
                        EnumFieldValue(
                            enum_type_id=enum_type.id,
                            label=value,
                            value=value,
                            sort_order=sort_order,
                            is_active=True,
                            is_deleted=False,
                            created_by="integration_test",
                            updated_by="integration_test",
                        )
                    )
                    continue

                value_obj.label = value
                value_obj.sort_order = sort_order
                value_obj.is_active = True
                value_obj.is_deleted = False
                value_obj.updated_by = "integration_test"

        db_session.commit()

    @staticmethod
    def _create_ownership(db_session, suffix: str) -> Ownership:
        ownership = Ownership(
            name=f"生命周期权属方-{suffix}",
            code=f"AL-{suffix}",
            short_name=f"AL{suffix[:4]}",
            data_status="正常",
        )
        db_session.add(ownership)
        db_session.commit()
        db_session.refresh(ownership)
        return ownership

    @staticmethod
    def _create_asset_payload(
        *,
        suffix: str,
        ownership_id: str,
        organization_id: str | None = None,
        property_nature: str = "经营类",
        usage_status: str = "出租",
        address_detail: str | None = None,
        address: str | None = None,
    ) -> dict[str, object]:
        detail = (
            address_detail
            if address_detail is not None
            else f"生命周期地址明细-{suffix}"
        )
        payload: dict[str, object] = {
            "ownership_id": ownership_id,
            "asset_name": f"生命周期资产-{suffix}",
            "address_detail": detail,
            "ownership_status": "已确权",
            "property_nature": property_nature,
            "usage_status": usage_status,
            "business_category": f"生命周期业态-{suffix}",
            "data_status": "正常",
            "created_by": "integration_test",
        }
        if address is not None:
            payload["address"] = address
        if organization_id is not None and organization_id.strip() != "":
            payload["organization_id"] = organization_id
        return payload

    def test_asset_create_with_address_only_should_use_legacy_address_fallback(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        db_session,
        test_data,
    ) -> None:
        suffix = uuid4().hex[:8]
        self._ensure_asset_enum_data(db_session)
        ownership = self._create_ownership(db_session, suffix)
        organization_id = str(test_data["organization"].id)
        payload = self._create_asset_payload(
            suffix=f"{suffix}addr-only",
            ownership_id=ownership.id,
            organization_id=organization_id,
            address_detail=None,
            address=f"仅地址字段-{suffix}",
        )
        payload.pop("address_detail", None)

        response = authenticated_client.post(
            "/api/v1/assets",
            json=payload,
            headers=csrf_headers,
        )

        assert response.status_code == 201
        created = response.json()
        created_id = created.get("id")
        assert isinstance(created_id, str)

        created_address = created.get("address")
        assert isinstance(created_address, str)

        address_handler = SensitiveDataHandler(searchable_fields={"address"})
        decrypted_created_address = address_handler.decrypt_field(
            "address", created_address
        )
        assert isinstance(decrypted_created_address, str)
        assert decrypted_created_address == payload["address"]

        detail_response = authenticated_client.get(f"/api/v1/assets/{created_id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        detail_address = detail_payload.get("address")
        assert isinstance(detail_address, str)

        decrypted_detail_address = address_handler.decrypt_field("address", detail_address)
        assert isinstance(decrypted_detail_address, str)
        assert decrypted_detail_address == payload["address"]

    def test_asset_create_with_blank_legacy_address_should_return_422(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        db_session,
        test_data,
    ) -> None:
        suffix = uuid4().hex[:8]
        self._ensure_asset_enum_data(db_session)
        ownership = self._create_ownership(db_session, suffix)
        organization_id = str(test_data["organization"].id)
        payload = self._create_asset_payload(
            suffix=f"{suffix}blank-address",
            ownership_id=ownership.id,
            organization_id=organization_id,
            address_detail=None,
            address="   ",
        )
        payload.pop("address_detail", None)

        response = authenticated_client.post(
            "/api/v1/assets",
            json=payload,
            headers=csrf_headers,
        )

        assert response.status_code == 422
        response_data = response.json()
        assert response_data.get("success") is False
        error = response_data.get("error", {})
        assert isinstance(error, dict)
        assert error.get("code") == "VALIDATION_ERROR"
        details = error.get("details", {})
        assert isinstance(details, dict)
        field_errors = details.get("field_errors", {})
        assert isinstance(field_errors, dict)
        address_detail_errors = field_errors.get("address_detail", [])
        assert isinstance(address_detail_errors, list)
        assert "required_for_address_composition" in address_detail_errors

    def test_asset_create_should_ignore_manual_address_and_use_composed_value(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        db_session,
        test_data,
    ) -> None:
        suffix = uuid4().hex[:8]
        self._ensure_asset_enum_data(db_session)
        ownership = self._create_ownership(db_session, suffix)
        organization_id = str(test_data["organization"].id)
        detail = f"系统拼接地址明细-{suffix}"
        manual_address = f"伪造地址-{suffix}"
        payload = self._create_asset_payload(
            suffix=f"{suffix}compose",
            ownership_id=ownership.id,
            organization_id=organization_id,
            address_detail=detail,
            address=manual_address,
        )

        create_response = authenticated_client.post(
            "/api/v1/assets",
            json=payload,
            headers=csrf_headers,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        created_id = created.get("id")
        assert isinstance(created_id, str)
        created_address = created.get("address")
        assert isinstance(created_address, str)
        address_handler = SensitiveDataHandler(searchable_fields={"address"})
        decrypted_created_address = address_handler.decrypt_field(
            "address", created_address
        )
        assert isinstance(decrypted_created_address, str)
        assert decrypted_created_address == detail
        assert decrypted_created_address != manual_address

        detail_response = authenticated_client.get(f"/api/v1/assets/{created_id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        detail_address = detail_payload.get("address")
        assert isinstance(detail_address, str)
        decrypted_detail_address = address_handler.decrypt_field("address", detail_address)
        assert isinstance(decrypted_detail_address, str)
        assert decrypted_detail_address == detail

    def test_complete_asset_lifecycle(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        db_session,
        test_data,
    ) -> None:
        suffix = uuid4().hex[:8]
        self._ensure_asset_enum_data(db_session)
        ownership = self._create_ownership(db_session, suffix)
        organization_id = str(test_data["organization"].id)
        payload = self._create_asset_payload(
            suffix=suffix,
            ownership_id=ownership.id,
            organization_id=organization_id,
        )

        create_response = authenticated_client.post(
            "/api/v1/assets",
            json=payload,
            headers=csrf_headers,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        asset_id = created.get("id")
        assert isinstance(asset_id, str)
        assert created.get("asset_name") == payload["asset_name"]

        detail_response = authenticated_client.get(f"/api/v1/assets/{asset_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail.get("id") == asset_id

        update_response = authenticated_client.put(
            f"/api/v1/assets/{asset_id}",
            json={"usage_status": "自用", "updated_by": "integration_test"},
            headers=csrf_headers,
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated.get("id") == asset_id
        assert updated.get("usage_status") == "自用"

        delete_response = authenticated_client.delete(
            f"/api/v1/assets/{asset_id}",
            headers=csrf_headers,
        )
        assert delete_response.status_code == 204

        deleted_detail_response = authenticated_client.get(f"/api/v1/assets/{asset_id}")
        assert deleted_detail_response.status_code == 404

    def test_asset_search_and_filter_integration(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        db_session,
        test_data,
    ) -> None:
        suffix = uuid4().hex[:8]
        self._ensure_asset_enum_data(db_session)
        ownership = self._create_ownership(db_session, suffix)
        organization_id = str(test_data["organization"].id)

        payload_a = self._create_asset_payload(
            suffix=f"{suffix}a",
            ownership_id=ownership.id,
            organization_id=organization_id,
            usage_status="出租",
        )
        payload_b = self._create_asset_payload(
            suffix=f"{suffix}b",
            ownership_id=ownership.id,
            organization_id=organization_id,
            usage_status="闲置",
        )

        created_asset_ids: list[str] = []
        for payload in (payload_a, payload_b):
            response = authenticated_client.post(
                "/api/v1/assets",
                json=payload,
                headers=csrf_headers,
            )
            assert response.status_code == 201
            created = response.json()
            created_id = created.get("id")
            assert isinstance(created_id, str)
            created_asset_ids.append(created_id)

        search_response = authenticated_client.get(
            f"/api/v1/assets?page=1&page_size=20&search={suffix}"
        )
        assert search_response.status_code == 200
        search_payload = search_response.json()
        assert search_payload.get("success") is True
        search_items = search_payload.get("data", {}).get("items", [])
        assert isinstance(search_items, list)
        search_item_ids = {
            item.get("id")
            for item in search_items
            if isinstance(item, dict) and item.get("id") is not None
        }
        assert set(created_asset_ids).issubset(search_item_ids)

        filter_response = authenticated_client.get(
            "/api/v1/assets?page=1&page_size=20"
            f"&search={suffix}&usage_status=闲置"
        )
        assert filter_response.status_code == 200
        filter_payload = filter_response.json()
        assert filter_payload.get("success") is True
        filter_items = filter_payload.get("data", {}).get("items", [])
        assert isinstance(filter_items, list)
        assert any(
            item.get("id") in created_asset_ids
            for item in filter_items
            if isinstance(item, dict)
        )

        for asset_id in created_asset_ids:
            response = authenticated_client.delete(
                f"/api/v1/assets/{asset_id}",
                headers=csrf_headers,
            )
            assert response.status_code == 204
