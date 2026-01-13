"""
Property Certificate Extractor Adapter
产权证/不动产权证提取适配器

继承 BaseVisionAdapter，使用产权证专用 Prompt
"""

import logging
from typing import Any

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

    def __init__(self):
        self._vision_service = get_qwen_vision_service()
        logger.info("PropertyCertAdapter initialized with Qwen Vision")

    @property
    def vision_service(self) -> Any:
        return self._vision_service

    @property
    def provider_name(self) -> str:
        return "qwen_vl_property_cert"

    @property
    def api_key_env_name(self) -> str:
        return "DASHSCOPE_API_KEY"
