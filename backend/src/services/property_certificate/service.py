"""
Property Certificate Service
产权证业务逻辑服务
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session
from src.crud.property_certificate import property_certificate_crud
from src.crud.property_owner import property_owner_crud
from src.models.property_certificate import PropertyCertificate, PropertyOwner, CertificateType
from src.schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
    CertificateExtractionResult,
    CertificateImportConfirm,
)
from src.services.property_certificate.validator import PropertyCertificateValidator
from src.services.property_certificate.matcher import AssetMatchingService
from src.services.document.extractors.property_cert_adapter import PropertyCertAdapter
from src.services.llm_prompt.prompt_manager import PromptManager


class PropertyCertificateService:
    """产权证服务"""

    def __init__(self, db: Session):
        self.db = db
        self.prompt_manager = PromptManager(db)
        self.asset_matcher = AssetMatchingService(db)
        self.adapter = PropertyCertAdapter()

    async def extract_from_file(
        self,
        file_path: str,
        filename: str
    ) -> CertificateExtractionResult:
        """从文件提取产权证信息"""
        # 1. Detect certificate type
        cert_type = await self._detect_certificate_type(file_path)

        # 2. Get appropriate prompt
        prompt = self.prompt_manager.get_active_prompt(
            doc_type="PROPERTY_CERT",
            metadata={"certificate_type": cert_type.value}
        )

        # 3. Extract fields using adapter
        extracted_data = await self.adapter.extract(file_path, prompt)

        # 4. Validate
        validation = PropertyCertificateValidator.validate_extracted_fields(
            extracted_data, cert_type
        )

        # 5. Match assets
        asset_matches = self.asset_matcher.find_matches(
            extracted_data.get("property_address"),
            extracted_data.get("property_name")
        )

        # 6. Generate session
        session_id = str(uuid.uuid4())

        # TODO: Cache extraction result (Redis or in-memory)

        return CertificateExtractionResult(
            session_id=session_id,
            certificate_type=cert_type,
            extracted_data=extracted_data,
            confidence_score=prompt.avg_confidence if prompt else 0.8,
            asset_matches=[{
                "asset_id": m.asset_id,
                "name": m.name,
                "address": m.address,
                "confidence": m.confidence,
                "match_reasons": m.match_reasons
            } for m in asset_matches],
            validation_errors=validation.errors,
            warnings=validation.warnings
        )

    async def confirm_import(
        self,
        data: CertificateImportConfirm
    ) -> PropertyCertificate:
        """确认导入，创建产权证"""
        # 1. Create certificate
        cert_data = PropertyCertificateCreate(**data.extracted_data)
        certificate = property_certificate_crud.create(self.db, obj_in=cert_data)

        # 2. Link or create asset
        if data.create_new_asset:
            # TODO: Create asset from certificate data
            pass
        elif data.asset_link_id:
            # TODO: Link existing asset
            pass

        # 3. Create/link owners
        for owner_data in data.owners:
            # TODO: Handle owner creation/linking
            pass

        return certificate

    async def _detect_certificate_type(self, file_path: str) -> CertificateType:
        """AI检测证书类型"""
        # TODO: Implement type detection using LLM
        # For MVP, default to REAL_ESTATE
        return CertificateType.REAL_ESTATE