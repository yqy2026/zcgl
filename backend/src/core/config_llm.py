"""Optional DeepSeek text-stage and WeCom settings."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class LlmSettings(BaseModel):
    """Settings for the only remaining document LLM integration."""

    LLM_TRIGGER_THRESHOLD: float = Field(
        default=0.65, json_schema_extra={"env": "LLM_TRIGGER_THRESHOLD"}
    )
    WECOM_ENABLED: bool = Field(
        default=False, json_schema_extra={"env": "WECOM_ENABLED"}
    )
    WECOM_CORP_ID: str | None = Field(default=None, json_schema_extra={"env": "WECOM_CORP_ID"})
    WECOM_AGENT_ID: str | None = Field(default=None, json_schema_extra={"env": "WECOM_AGENT_ID"})
    WECOM_SECRET: str | None = Field(default=None, json_schema_extra={"env": "WECOM_SECRET"})
    WECOM_TEST_TOUSER: str | None = Field(default=None, json_schema_extra={"env": "WECOM_TEST_TOUSER"})
    WECOM_WEBHOOK_URL: str | None = Field(default=None, json_schema_extra={"env": "WECOM_WEBHOOK_URL"})
    WECOM_MENTION_ALL: bool = Field(default=False, json_schema_extra={"env": "WECOM_MENTION_ALL"})

    DOCUMENT_LLM_ENABLED: bool = Field(
        default=False, json_schema_extra={"env": "DOCUMENT_LLM_ENABLED"}
    )
    DEEPSEEK_API_KEY: str | None = Field(
        default=None, json_schema_extra={"env": "DEEPSEEK_API_KEY"}
    )
    DEEPSEEK_MODEL: str | None = Field(
        default=None, json_schema_extra={"env": "DEEPSEEK_MODEL"}
    )
    DEEPSEEK_BASE_URL: str = Field(
        default="https://api.deepseek.com/v1",
        json_schema_extra={"env": "DEEPSEEK_BASE_URL"},
    )

    @model_validator(mode="after")
    def validate_document_llm_configuration(self) -> LlmSettings:
        if not self.DOCUMENT_LLM_ENABLED:
            return self
        base_url = urlparse(self.DEEPSEEK_BASE_URL)
        if not self.DEEPSEEK_API_KEY:
            raise PydanticCustomError(
                "document_llm_key_missing",
                "DEEPSEEK_API_KEY is required when DOCUMENT_LLM_ENABLED=true",
                {},
            )
        if self.DEEPSEEK_MODEL != "deepseek-v4-flash":
            raise PydanticCustomError(
                "document_llm_model_invalid",
                "DEEPSEEK_MODEL must be deepseek-v4-flash when DOCUMENT_LLM_ENABLED=true",
                {},
            )
        if base_url.scheme != "https" or base_url.hostname != "api.deepseek.com":
            raise PydanticCustomError(
                "document_llm_base_url_invalid",
                "DEEPSEEK_BASE_URL must use the official DeepSeek API host",
                {},
            )
        return self

    @model_validator(mode="after")
    def validate_wecom_configuration(self) -> LlmSettings:
        if self.WECOM_ENABLED and (
            not self.WECOM_CORP_ID or not self.WECOM_AGENT_ID or not self.WECOM_SECRET
        ):
            logger.warning("WeCom is enabled but application credentials are incomplete")
        if self.WECOM_WEBHOOK_URL:
            logger.warning("WECOM_WEBHOOK_URL group robot delivery is retired and ignored")
        return self
