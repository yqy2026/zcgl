"""
LLM prompt CRUD operations.
"""

from ..models.llm_prompt import PromptTemplate
from ..schemas.llm_prompt import PromptTemplateCreate, PromptTemplateUpdate
from .base import CRUDBase


class CRUDPromptTemplate(
    CRUDBase[PromptTemplate, PromptTemplateCreate, PromptTemplateUpdate]
):
    """CRUD for PromptTemplate."""


prompt_template_crud = CRUDPromptTemplate(PromptTemplate)
