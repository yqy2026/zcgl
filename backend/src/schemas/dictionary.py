"""
统一字典管理的 Schema 定义
提供类型安全的数据模型
"""

from pydantic import BaseModel, Field


class DictionaryOptionCreate(BaseModel):
    """字典选项创建模型 - 类型安全"""

    label: str = Field(..., min_length=1, max_length=100, description="显示标签")
    value: str = Field(..., min_length=1, max_length=100, description="选项值")
    code: str | None = Field(None, max_length=50, description="选项编码")
    description: str | None = Field(None, description="描述")
    sort_order: int = Field(default=0, ge=0, description="排序序号")
    color: str | None = Field(None, max_length=20, description="颜色标识")
    icon: str | None = Field(None, max_length=50, description="图标")
    is_active: bool = Field(default=True, description="是否启用")


class DictionaryOptionResponse(BaseModel):
    """字典选项响应模型"""

    label: str
    value: str
    code: str | None = None
    sort_order: int = 0
    color: str | None = None
    icon: str | None = None


class SimpleDictionaryCreate(BaseModel):
    """简单字典创建模型 - 类型安全版本"""

    options: list[DictionaryOptionCreate] = Field(..., description="字典选项列表")
    description: str | None = Field(None, description="字典描述")


class DictionaryValueCreate(BaseModel):
    """单个字典值创建模型"""

    label: str = Field(..., min_length=1, max_length=100, description="显示标签")
    value: str = Field(..., min_length=1, max_length=100, description="选项值")
    code: str | None = Field(None, max_length=50, description="选项编码")
    description: str | None = Field(None, description="描述")
    sort_order: int = Field(default=999, ge=0, description="排序序号")
    color: str | None = Field(None, max_length=20, description="颜色标识")
    icon: str | None = Field(None, max_length=50, description="图标")
    is_active: bool = Field(default=True, description="是否启用")
