"""
Property Certificate Service
产权证服务层

业务逻辑：
- extract_from_file: 上传并提取产权证信息
- confirm_import: 确认导入，创建产权证记录
"""

import logging
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.exception_handler import BusinessValidationError, ResourceNotFoundError
from ...crud.asset import asset_crud
from ...crud.property_certificate import property_certificate_crud
from ...crud.query_builder import PartyFilter
from ...models.asset import Asset
from ...models.property_certificate import PropertyCertificate
from ...schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
)
from ...services.document.extractors.property_cert_adapter import PropertyCertAdapter
from ...services.document.ocr_extraction_service import OCRExtractionService
from ...services.llm_prompt.prompt_manager import PromptManager
from ...services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)


class PropertyCertificateService:
    """
    产权证服务

    负责产权证文件的AI提取和导入流程
    """

    def __init__(self, db: AsyncSession):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.extractor = PropertyCertAdapter()
        self.ocr_extractor = OCRExtractionService()

    @staticmethod
    def _is_fail_closed_party_filter(party_filter: PartyFilter | None) -> bool:
        if party_filter is None:
            return False
        return (
            len(
                [
                    org_id
                    for org_id in party_filter.party_ids
                    if str(org_id).strip() != ""
                ]
            )
            == 0
        )

    async def _resolve_party_filter(
        self,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            self.db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
        )

    async def list_certificates(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[PropertyCertificate]:
        """获取产权证列表"""
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return []

        return await property_certificate_crud.get_multi(
            self.db,
            skip=skip,
            limit=limit,
            party_filter=resolved_party_filter,
        )

    async def get_certificate(
        self,
        certificate_id: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> PropertyCertificate | None:
        """获取单个产权证"""
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return None

        return await property_certificate_crud.get(
            self.db,
            certificate_id,
            party_filter=resolved_party_filter,
        )

    async def create_certificate(
        self,
        certificate: PropertyCertificateCreate,
        *,
        created_by: str | None = None,
        organization_id: str | None = None,
    ) -> PropertyCertificate:
        """创建产权证"""
        payload = certificate.model_dump()
        payload.pop("organization_id", None)  # DEPRECATED alias
        if created_by is not None and created_by.strip() != "":
            payload["created_by"] = created_by
        if organization_id is not None and organization_id.strip() != "":
            logger.debug(
                "Ignoring deprecated organization_id during certificate creation: %s",
                organization_id,
            )

        return await property_certificate_crud.create(
            self.db,
            obj_in=payload,
        )

    async def update_certificate(
        self,
        certificate: PropertyCertificate,
        update: PropertyCertificateUpdate,
    ) -> PropertyCertificate:
        """更新产权证"""
        return await property_certificate_crud.update(
            self.db, db_obj=certificate, obj_in=update
        )

    async def delete_certificate(self, certificate_id: str) -> None:
        """删除产权证"""
        await property_certificate_crud.remove(self.db, id=certificate_id)

    async def extract_from_file(self, file_path: str, filename: str) -> dict[str, Any]:
        """
        从文件提取产权证信息

        Args:
            file_path: 上传文件的临时路径
            filename: 原始文件名

        Returns:
            提取结果字典，包含：
            - success: bool
            - data: dict (提取的字段)
            - confidence: float
            - raw_response: Any
            - extraction_method: str
        """
        try:
            logger.info(f"开始提取产权证: {filename}")

            if settings.GLM_OCR_ENABLE:
                ocr_result = await self.ocr_extractor.extract_property_cert(file_path)
                if ocr_result.get("success"):
                    logger.info(
                        "产权证 OCR 提取完成: %s, confidence=%s",
                        filename,
                        ocr_result.get("confidence", 0.0),
                    )
                    return {
                        "success": True,
                        "data": ocr_result.get("extracted_fields", {}),
                        "confidence": ocr_result.get("confidence") or 0.0,
                        "raw_response": ocr_result.get("raw_llm_json"),
                        "extraction_method": ocr_result.get(
                            "extraction_method", "ocr_text"
                        ),
                        "filename": filename,
                    }
                logger.info(
                    "产权证 OCR 提取失败，回退到视觉模型: %s",
                    ocr_result.get("error"),
                )

            prompt_manager = PromptManager()
            prompt = await prompt_manager.get_active_prompt_async(
                self.db, doc_type="PROPERTY_CERT", provider="qwen"
            )
            if not prompt:
                raise ResourceNotFoundError(
                    "Prompt",
                    "PROPERTY_CERT/qwen",
                    details={"doc_type": "PROPERTY_CERT", "provider": "qwen"},
                )

            result = await self.extractor.extract(file_path, prompt=prompt)

            logger.info(
                f"产权证提取完成: {filename}, confidence={result.get('confidence', 0)}"
            )

            return {
                "success": result.get("success", False),
                "data": result.get("extracted_fields", {}),
                "confidence": result.get("confidence") or 0.0,
                "raw_response": result.get("raw_response"),
                "extraction_method": result.get("extraction_method", "unknown"),
                "filename": filename,
            }

        except Exception as e:
            logger.error(f"提取产权证失败: {filename}, error={str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filename": filename,
            }

    async def confirm_import(
        self,
        data: dict[str, Any],
        *,
        created_by: str | None = None,
        organization_id: str | None = None,
    ) -> PropertyCertificate:
        """
        确认导入，创建产权证记录

        Args:
            data: 包含提取字段和用户确认信息的字典
                - extracted_data: 提取并确认后的字段数据
                - asset_ids: 需关联的资产ID列表
                - asset_link_id: 单个资产关联ID（UI兼容）
                - should_create_new_asset: 是否创建新资产（为 True 时忽略资产关联）
                - owners: 权利人信息列表 (可选)

        Returns:
            PropertyCertificate: 创建的产权证对象

        Raises:
            ValueError: 数据验证失败
            Exception: 数据库操作失败
        """
        extracted_data = data.get("extracted_data")
        if not isinstance(extracted_data, dict):
            raise BusinessValidationError(
                "缺少提取数据",
                field_errors={"extracted_data": ["缺少提取数据"]},
            )

        certificate_number = self._normalize_match_value(
            extracted_data.get("certificate_number")
        )
        owners_data = data.get("owners", [])
        should_create_new_asset = data.get("should_create_new_asset") is True
        asset_ids = [
            str(asset_id).strip()
            for asset_id in (data.get("asset_ids") or [])
            if str(asset_id).strip()
        ]
        asset_link_id = data.get("asset_link_id")
        if not should_create_new_asset and asset_link_id is not None:
            normalized_asset_link_id = str(asset_link_id).strip()
            if normalized_asset_link_id and normalized_asset_link_id not in asset_ids:
                asset_ids.append(normalized_asset_link_id)
        if should_create_new_asset:
            asset_ids = []

        if not certificate_number:
            raise BusinessValidationError(
                "缺少证书编号",
                field_errors={"certificate_number": ["缺少证书编号"]},
            )

        logger.info(f"确认导入产权证: {certificate_number}")
        try:
            existing = await property_certificate_crud.get_by_certificate_number_async(
                self.db, certificate_number
            )
            if existing:
                logger.warning(f"产权证已存在: {certificate_number}")
                return existing

            confidence_raw = extracted_data.get("confidence")
            try:
                extraction_confidence = (
                    float(confidence_raw) if confidence_raw is not None else None
                )
            except (TypeError, ValueError):
                extraction_confidence = None

            certificate_create_data = {
                "certificate_number": certificate_number,
                "certificate_type": str(
                    extracted_data.get("certificate_type") or "other"
                ),
                "extraction_confidence": extraction_confidence,
                "extraction_source": "llm",
                "is_verified": False,
                "registration_date": self._parse_date(
                    extracted_data.get("registration_date")
                ),
                "property_address": extracted_data.get("property_address"),
                "property_type": extracted_data.get("property_type"),
                "building_area": extracted_data.get("building_area"),
                "floor_info": extracted_data.get("floor_info"),
                "land_area": extracted_data.get("land_area"),
                "land_use_type": extracted_data.get("land_use_type"),
                "land_use_term_start": self._parse_date(
                    extracted_data.get("land_use_term_start")
                ),
                "land_use_term_end": self._parse_date(
                    extracted_data.get("land_use_term_end")
                ),
                "co_ownership": extracted_data.get("co_ownership"),
                "restrictions": extracted_data.get("restrictions"),
                "remarks": extracted_data.get("remarks"),
                "created_by": created_by,
            }

            owner_ids = [
                str(owner_data.get("party_id")).strip()
                for owner_data in owners_data
                if str(owner_data.get("party_id") or "").strip() != ""
            ]

            certificate_create = PropertyCertificateCreate.model_validate(
                certificate_create_data
            )
            certificate = await property_certificate_crud.create_with_owners_async(
                self.db,
                obj_in=certificate_create,
                owner_ids=owner_ids if owner_ids else None,
                asset_ids=asset_ids if asset_ids else None,
                organization_id=organization_id,
            )

            logger.info(f"产权证创建成功: {certificate.id} - {certificate_number}")
            return certificate
        except BusinessValidationError as e:
            logger.error(f"数据验证失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"创建产权证失败: certificate_number={data.get('certificate_number')}, error={str(e)}"
            )
            raise

    def _parse_date(self, date_str: str | None) -> date | None:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串 (格式: YYYY-MM-DD 或 YYYY/MM/DD)

        Returns:
            date | None: 解析后的日期对象
        """
        if not date_str:
            return None

        from datetime import datetime

        # 尝试常见日期格式
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"无法解析日期: {date_str}")
        return None

    async def match_assets(
        self, extracted_data: dict[str, Any], limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        根据提取结果匹配资产

        Args:
            extracted_data: 提取字段数据
            limit: 返回匹配数量上限

        Returns:
            list[dict[str, Any]]: 匹配结果列表
        """

        address_raw = extracted_data.get("property_address")
        owner_raw = extracted_data.get("owner_name")

        address = self._normalize_match_value(address_raw)
        owner_name = self._normalize_match_value(owner_raw)

        if not address and not owner_name:
            return []

        candidates: dict[str, dict[str, Any]] = {}
        candidate_limit = max(limit * 4, 10)

        if address:
            for asset in await self._fetch_assets_by_field(
                "address", address_raw, limit=candidate_limit
            ):
                entry = candidates.setdefault(
                    asset.id, {"asset": asset, "fields": set()}
                )
                entry["fields"].add("address")

        if owner_name:
            for asset in await self._fetch_assets_by_field(
                "ownership_entity", owner_raw, limit=candidate_limit
            ):
                entry = candidates.setdefault(
                    asset.id, {"asset": asset, "fields": set()}
                )
                entry["fields"].add("ownership_entity")

        matches: list[dict[str, Any]] = []
        for entry in candidates.values():
            asset = entry["asset"]
            fields = entry["fields"]

            address_quality = None
            owner_quality = None
            match_reasons: list[str] = []

            if "address" in fields and address:
                address_quality = (
                    self._match_quality(address, getattr(asset, "address", None))
                    or "exact"
                )
                match_reasons.append("地址匹配")

            if "ownership_entity" in fields and owner_name:
                owner_quality = (
                    self._match_quality(
                        owner_name, getattr(asset, "ownership_entity", None)
                    )
                    or "exact"
                )
                match_reasons.append("权属方匹配")

            confidence = self._calculate_match_confidence(
                address_quality, owner_quality
            )
            if confidence <= 0:
                continue

            matches.append(
                {
                    "asset_id": asset.id,
                    "name": getattr(asset, "property_name", "") or "",
                    "address": getattr(asset, "address", "") or "",
                    "confidence": confidence,
                    "match_reasons": match_reasons,
                }
            )

        matches.sort(key=lambda item: item["confidence"], reverse=True)
        return matches[:limit]

    async def _fetch_assets_by_field(
        self, field_name: str, raw_value: Any, limit: int = 20
    ) -> list[Asset]:
        """
        根据字段值获取资产列表（处理加密字段）

        安全说明：自动过滤已删除资产，避免泄露已删除数据
        """
        candidates = self._build_value_candidates(raw_value)
        if not candidates:
            return []

        if field_name == "ownership_entity":
            query_value = candidates[0]
            return await asset_crud.get_by_ownership_name_like_async(
                self.db,
                ownership_name=query_value,
                limit=limit,
                include_deleted=False,
                decrypt=True,
            )
        assets, used_blind_index = await asset_crud.search_by_field_with_candidates_async(
            self.db,
            field_name=field_name,
            candidates=candidates,
            limit=limit,
            include_deleted=False,
            decrypt=True,
        )

        if used_blind_index:
            normalized_candidates = [
                self._normalize_match_value(candidate).lower()
                for candidate in candidates
                if self._normalize_match_value(candidate)
            ]
            if normalized_candidates:
                filtered_assets = []
                for asset in assets:
                    field_value = getattr(asset, field_name, None)
                    normalized_value = self._normalize_match_value(field_value).lower()
                    if normalized_value and any(
                        candidate in normalized_value
                        for candidate in normalized_candidates
                    ):
                        filtered_assets.append(asset)
                assets = filtered_assets
        return assets

    def _build_value_candidates(self, raw_value: Any) -> list[str]:
        normalized = self._normalize_match_value(raw_value)
        if not normalized:
            return []
        candidates = {normalized}
        raw_text = str(raw_value).strip() if raw_value is not None else ""
        if raw_text and raw_text != normalized:
            candidates.add(raw_text)
        return list(candidates)

    def _normalize_match_value(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        return " ".join(text.split())

    def _match_quality(self, needle: str, haystack: str | None) -> str | None:
        if not needle or not haystack:
            return None
        norm_needle = self._normalize_match_value(needle).lower()
        norm_haystack = self._normalize_match_value(haystack).lower()
        if not norm_needle or not norm_haystack:
            return None
        if norm_needle == norm_haystack:
            return "exact"
        if norm_needle in norm_haystack or norm_haystack in norm_needle:
            return "partial"
        return None

    def _calculate_match_confidence(
        self, address_quality: str | None, owner_quality: str | None
    ) -> float:
        if address_quality and owner_quality:
            base = 0.9
        elif address_quality:
            base = 0.75
        elif owner_quality:
            base = 0.65
        else:
            return 0.0

        if address_quality == "partial" or owner_quality == "partial":
            base -= 0.1

        return max(min(base, 0.95), 0.5)
