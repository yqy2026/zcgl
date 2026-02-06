"""
Unit tests for Asset schema attachment fields.
"""

from datetime import datetime

from src.schemas.asset import AssetCreate, AssetResponse, AssetUpdate


class TestAssetSchemaAttachments:
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

    def test_asset_response_includes_attachments_fields(self) -> None:
        now = datetime.utcnow()
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
