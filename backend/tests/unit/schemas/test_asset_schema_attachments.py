"""
Unit tests for Asset schema attachment fields.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.schemas.asset import AssetCreate, AssetResponse, AssetUpdate


class TestAssetSchemaAttachments:
    def test_asset_create_schema_excludes_legacy_fields(self) -> None:
        properties = AssetCreate.model_json_schema().get("properties", {})
        assert "wuyang_project_name" not in properties
        assert "description" not in properties

    def test_asset_response_schema_excludes_legacy_fields(self) -> None:
        properties = AssetResponse.model_json_schema().get("properties", {})
        assert "wuyang_project_name" not in properties
        assert "description" not in properties

    def test_asset_create_includes_attachments_fields(self) -> None:
        asset = AssetCreate(
            ownership_id="owner-001",
            property_name="测试物业",
            address="测试地址",
            ownership_status="已确权",
            property_nature="经营类",
            usage_status="出租",
            operation_agreement_attachments="receive-1.pdf,receive-2.pdf",
            terminal_contract_files="terminal-1.pdf",
        )

        payload = asset.model_dump()

        assert (
            payload["operation_agreement_attachments"]
            == "receive-1.pdf,receive-2.pdf"
        )
        assert payload["terminal_contract_files"] == "terminal-1.pdf"

    def test_asset_update_includes_attachments_fields(self) -> None:
        asset = AssetUpdate(
            operation_agreement_attachments="receive-3.pdf",
            terminal_contract_files="terminal-2.pdf,terminal-3.pdf",
        )

        payload = asset.model_dump(exclude_unset=True)

        assert payload["operation_agreement_attachments"] == "receive-3.pdf"
        assert payload["terminal_contract_files"] == "terminal-2.pdf,terminal-3.pdf"

    def test_asset_update_includes_management_entity_field(self) -> None:
        asset = AssetUpdate(management_entity="运营管理单位A")
        payload = asset.model_dump(exclude_unset=True)

        assert payload["management_entity"] == "运营管理单位A"

    def test_asset_response_includes_attachments_fields(self) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        asset = AssetResponse(
            id="asset-001",
            property_name="测试物业",
            address="测试地址",
            ownership_status="已确权",
            property_nature="经营类",
            usage_status="出租",
            created_at=now,
            updated_at=now,
            operation_agreement_attachments="receive-4.pdf",
            terminal_contract_files="terminal-4.pdf",
        )

        payload = asset.model_dump()

        assert payload["operation_agreement_attachments"] == "receive-4.pdf"
        assert payload["terminal_contract_files"] == "terminal-4.pdf"

    def test_asset_create_rejects_legacy_fields(self) -> None:
        with pytest.raises(ValidationError) as error:
            AssetCreate(
                ownership_id="owner-001",
                property_name="测试物业",
                address="测试地址",
                ownership_status="已确权",
                property_nature="经营类",
                usage_status="出租",
                wuyang_project_name="历史项目名",
                description="历史备注",
            )

        message = str(error.value)
        assert "wuyang_project_name->project_name" in message
        assert "description->notes" in message

    def test_asset_update_rejects_legacy_fields(self) -> None:
        with pytest.raises(ValidationError) as error:
            AssetUpdate(
                wuyang_project_name="历史项目名",
                description="历史备注",
            )

        message = str(error.value)
        assert "wuyang_project_name->project_name" in message
        assert "description->notes" in message
