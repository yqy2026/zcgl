"""
Property Certificate Extractor Adapter
产权证/不动产权证提取适配器

继承 BaseVisionAdapter，使用产权证专用 Prompt
"""

import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ....models.llm_prompt import PromptTemplate
from ....services.llm_prompt.prompt_manager import PromptManager
from ...core.qwen_vision_service import get_qwen_vision_service
from .base import BaseVisionAdapter

logger = logging.getLogger(__name__)


class PropertyCertAdapter(BaseVisionAdapter):
    """
    产权证提取适配器

    使用 Qwen Vision 服务提取产权证信息。
    可通过环境变量 DASHSCOPE_API_KEY 配置。
    """

    # 产权证专用提取 Prompt
    EXTRACTION_PROMPT_TEMPLATE = """请分析这份中国不动产权证/房产证图片，提取以下信息并返回JSON格式：

{{
    "certificate_number": "不动产权证号/房产证编号",
    "registration_date": "登记日期(YYYY-MM-DD)",

    "owner_name": "权利人姓名/单位名称",
    "owner_id_type": "证件类型(身份证/营业执照等)",
    "owner_id_number": "证件号码",

    "property_address": "坐落地址(完整地址)",
    "property_type": "用途(住宅/商业/工业/办公)",
    "building_area": "建筑面积(数字,平方米)",
    "land_area": "土地使用面积(数字,平方米)",
    "floor_info": "楼层信息",

    "land_use_type": "土地使用权类型(出让/划拨)",
    "land_use_term_start": "土地使用期限起(YYYY-MM-DD)",
    "land_use_term_end": "土地使用期限止(YYYY-MM-DD)",

    "co_ownership": "共有情况",
    "restrictions": "权利限制情况",
    "remarks": "备注"
}}

提取规则：
1. 日期格式统一使用 YYYY-MM-DD
2. 面积只填数字，不需要单位
3. 确保证件号码和证书编号完整准确
4. 找不到的字段填 null
5. 只返回JSON，不要其他说明{pages_hint}"""

    def __init__(self, db: Session | None = None):
        super().__init__()
        self._vision_service = get_qwen_vision_service()
        self.prompt_manager: PromptManager | None = None
        if db:
            self.prompt_manager = PromptManager()
        else:
            logger.warning(
                "PropertyCertAdapter initialized without PromptManager - will require explicit prompt"
            )

        logger.info("PropertyCertAdapter initialized with Qwen Vision")

    async def extract(
        self,
        file_path: str,
        max_pages: int = 10,
        batch_size: int = 3,
        dpi: int = 200,
        *,
        prompt: PromptTemplate | None = None,
        certificate_type: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        提取产权证信息

        Args:
            file_path: 文件路径
            prompt: 可选的Prompt模板（如果提供，直接使用）
            certificate_type: 产权证类型 (real_estate, land, etc.)
            **kwargs: 其他参数传递给基类的extract方法

        Returns:
            提取结果字典
        """
        # If explicit prompt provided, validate it
        if prompt:
            if not isinstance(prompt, PromptTemplate):
                raise ValueError("prompt must be a PromptTemplate instance")
            logger.info(f"Using provided prompt: {prompt.name} (v{prompt.version})")
        # Otherwise, get from database via PromptManager
        else:
            if not self.prompt_manager:
                raise ValueError(
                    "PromptManager not initialized - pass db to constructor or provide explicit prompt"
                )
            # Need db session for PromptManager
            db = kwargs.get("db")
            if not db:
                raise ValueError(
                    "db session required for PromptManager - pass via kwargs or constructor"
                )

            prompt = self.prompt_manager.get_active_prompt(
                db=db,
                doc_type="PROPERTY_CERT",
                provider="qwen",  # PropertyCertAdapter uses Qwen
            )

            if not prompt:
                raise ValueError(
                    f"No active prompt found for PROPERTY_CERT with provider qwen. "
                    f"Please ensure prompts are initialized (certificate_type={certificate_type})"
                )

            logger.info(
                f"Retrieved prompt from database: {prompt.name} (v{prompt.version})"
            )

        # Format user prompt with file name
        file_name = Path(file_path).name
        user_prompt = prompt.user_prompt_template.format(file_name=file_name)

        # Log the extraction
        logger.info(
            f"Extracting from {file_name} using prompt {prompt.name} "
            f"(certificate_type={certificate_type or 'real_estate'})"
        )

        # Override the base class method to use our custom prompts
        # We need to temporarily override the EXTRACTION_PROMPT_TEMPLATE
        original_template = self.EXTRACTION_PROMPT_TEMPLATE
        self.EXTRACTION_PROMPT_TEMPLATE = user_prompt

        try:
            # Call parent's extract method
            result = await super().extract(
                file_path,
                max_pages=max_pages,
                batch_size=batch_size,
                dpi=dpi,
                **kwargs,
            )
            # Add prompt metadata to result
            if result.get("success"):
                result["prompt_used"] = {
                    "id": prompt.id,
                    "name": prompt.name,
                    "version": prompt.version,
                    "certificate_type": certificate_type or "real_estate",
                }
            return result
        finally:
            # Restore original template
            self.EXTRACTION_PROMPT_TEMPLATE = original_template

    @property
    def vision_service(self) -> Any:
        return self._vision_service

    @property
    def provider_name(self) -> str:
        return "qwen_vl_property_cert"

    @property
    def api_key_env_name(self) -> str:
        return "DASHSCOPE_API_KEY"
