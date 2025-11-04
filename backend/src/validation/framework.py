from typing import Any

"""
数据验证框架
提供统一的验证机制和自定义验证器
"""

import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


# 创建自定义业务验证异常
class BusinessValidationError(Exception):
    """业务验证错误"""

    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationRule:
    """验证规则基类"""

    def __init__(
        self,
        name: str,
        description: str,
        required: bool = True,
        error_message: str = None,
    ):
        self.name = name
        self.description = description
        self.required = required
        self.error_message = error_message or f"{name} 验证失败"

    def validate(self, value: Any) -> bool:
        """执行验证"""
        raise NotImplementedError

    def get_error_message(self, value: Any = None) -> str:
        """获取错误消息"""
        return self.error_message


class RequiredRule(ValidationRule):
    """必填字段验证"""

    def validate(self, value: Any) -> bool:
        if self.required:
            return value is not None and value != ""
        return True


class LengthRule(ValidationRule):
    """长度验证"""

    def __init__(self, min_length: int = None, max_length: int = None, **kwargs):
        super().__init__("length", "字段长度验证", **kwargs)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any) -> bool:
        if value is None:
            return not self.required

        length = len(str(value))
        if self.min_length is not None and length < self.min_length:
            self.error_message = f"长度不能少于 {self.min_length} 个字符"
            return False
        if self.max_length is not None and length > self.max_length:
            self.error_message = f"长度不能超过 {self.max_length} 个字符"
            return False
        return True


class PatternRule(ValidationRule):
    """正则表达式验证"""

    def __init__(self, pattern: str, **kwargs):
        super().__init__("pattern", "正则表达式验证", **kwargs)
        self.pattern = re.compile(pattern)

    def validate(self, value: Any) -> bool:
        if value is None:
            return not self.required
        return bool(self.pattern.match(str(value)))


class RangeRule(ValidationRule):
    """数值范围验证"""

    def __init__(
        self,
        min_value: int | float | Decimal = None,
        max_value: int | float | Decimal = None,
        **kwargs,
    ):
        super().__init__("range", "数值范围验证", **kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> bool:
        if value is None:
            return not self.required

        try:
            num_value = float(value)
            if self.min_value is not None and num_value < self.min_value:
                self.error_message = f"值不能小于 {self.min_value}"
                return False
            if self.max_value is not None and num_value > self.max_value:
                self.error_message = f"值不能大于 {self.max_value}"
                return False
            return True
        except (ValueError, TypeError):
            self.error_message = "必须是有效的数字"
            return False


class EmailRule(PatternRule):
    """邮箱验证"""

    def __init__(self, **kwargs):
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        super().__init__(
            email_pattern, name="email", description="邮箱格式验证", **kwargs
        )
        self.error_message = "邮箱格式不正确"


class PhoneRule(PatternRule):
    """手机号验证"""

    def __init__(self, **kwargs):
        phone_pattern = r"^1[3-9]\d{9}$"
        super().__init__(
            phone_pattern, name="phone", description="手机号格式验证", **kwargs
        )
        self.error_message = "手机号格式不正确"


class DateRule(ValidationRule):
    """日期验证"""

    def __init__(self, date_format: str = "%Y-%m-%d", **kwargs):
        super().__init__("date", "日期格式验证", **kwargs)
        self.date_format = date_format

    def validate(self, value: Any) -> bool:
        if value is None:
            return not self.required

        if isinstance(value, (datetime, date)):
            return True

        try:
            datetime.strptime(str(value), self.date_format)
            return True
        except ValueError:
            self.error_message = f"日期格式不正确，应为 {self.date_format}"
            return False


class EnumRule(ValidationRule):
    """枚举值验证"""

    def __init__(self, allowed_values: list[Any], **kwargs):
        super().__init__("enum", "枚举值验证", **kwargs)
        self.allowed_values = allowed_values

    def validate(self, value: Any) -> bool:
        if value is None:
            return not self.required
        if value not in self.allowed_values:
            self.error_message = (
                f"值必须是以下选项之一: {', '.join(map(str, self.allowed_values))}"
            )
            return False
        return True


class FileRule(ValidationRule):
    """文件验证"""

    def __init__(
        self, allowed_extensions: list[str] = None, max_size_mb: int = None, **kwargs
    ):
        super().__init__("file", "文件验证", **kwargs)
        self.allowed_extensions = allowed_extensions or []
        self.max_size_mb = max_size_mb

    def validate(self, value: Any) -> bool:
        if value is None:
            return not self.required

        # 如果是UploadFile对象
        if hasattr(value, "filename") and hasattr(value, "size"):
            # 检查文件扩展名
            if self.allowed_extensions:
                filename = value.filename
                if "." not in filename:
                    self.error_message = "文件必须有扩展名"
                    return False

                ext = filename.split(".")[-1].lower()
                if ext not in self.allowed_extensions:
                    self.error_message = (
                        f"文件类型不支持，允许的类型: "
                        f"{', '.join(self.allowed_extensions)}"
                    )
                    return False

            # 检查文件大小
            if self.max_size_mb and hasattr(value, "size"):
                size_mb = value.size / (1024 * 1024)
                if size_mb > self.max_size_mb:
                    self.error_message = f"文件大小不能超过 {self.max_size_mb}MB"
                    return False

        return True


class ValidationSchema:
    """验证模式"""

    def __init__(self, name: str):
        self.name = name
        self.rules: dict[str, list[ValidationRule]] = {}
        self.custom_validators: dict[str, Callable] = {}

    def add_rule(self, field: str, rule: ValidationRule):
        """添加验证规则"""
        if field not in self.rules:
            self.rules[field] = []
        self.rules[field].append(rule)

    def add_validator(self, field: str, validator: Callable):
        """添加自定义验证器"""
        self.custom_validators[field] = validator

    def validate(self, data: dict[str, Any]) -> dict[str, list[str]]:
        """验证数据"""
        errors = {}

        # 验证每个字段
        for field, rules in self.rules.items():
            field_errors = []
            value = data.get(field)

            for rule in rules:
                if not rule.validate(value):
                    field_errors.append(rule.get_error_message(value))

            if field_errors:
                errors[field] = field_errors

        # 执行自定义验证器
        for field, validator in self.custom_validators.items():
            try:
                validator(data.get(field), data)
            except Exception as e:
                if field not in errors:
                    errors[field] = []
                errors[field].append(str(e))

        return errors


class ValidationFramework:
    """验证框架"""

    def __init__(self):
        self.schemas: dict[str, ValidationSchema] = {}
        self.global_validators: dict[str, Callable] = {}

    def register_schema(self, schema: ValidationSchema):
        """注册验证模式"""
        self.schemas[schema.name] = schema

    def register_validator(self, name: str, validator: Callable):
        """注册全局验证器"""
        self.global_validators[name] = validator

    def validate(self, schema_name: str, data: dict[str, Any]) -> dict[str, list[str]]:
        """验证数据"""
        if schema_name not in self.schemas:
            raise ValueError(f"未知的验证模式: {schema_name}")

        schema = self.schemas[schema_name]
        return schema.validate(data)

    def get_schema(self, schema_name: str) -> ValidationSchema:
        """获取验证模式"""
        if schema_name not in self.schemas:
            raise ValueError(f"未知的验证模式: {schema_name}")
        return self.schemas[schema_name]

    def create_schema_from_pydantic(
        self, model_class: type[BaseModel]
    ) -> ValidationSchema:
        """从Pydantic模型创建验证模式"""
        schema = ValidationSchema(model_class.__name__)

        # 从Pydantic模型字段创建验证规则
        for field_name, field_info in model_class.model_fields.items():
            # 必填验证
            if not field_info.default:
                schema.add_rule(
                    field_name,
                    RequiredRule(
                        name="required", description="必填字段验证", required=True
                    ),
                )

            # 字符串长度验证
            if hasattr(field_info, "max_length") and field_info.max_length:
                schema.add_rule(
                    field_name,
                    LengthRule(max_length=field_info.max_length, required=False),
                )

            # 数值范围验证
            if hasattr(field_info, "ge") or hasattr(field_info, "le"):
                schema.add_rule(
                    field_name,
                    RangeRule(
                        min_value=getattr(field_info, "ge", None),
                        max_value=getattr(field_info, "le", None),
                        required=False,
                    ),
                )

        return schema


# 创建全局验证框架实例
validation_framework = ValidationFramework()


# 预定义的验证模式
def create_asset_validation_schema() -> ValidationSchema:
    """创建资产数据验证模式"""
    schema = ValidationSchema("asset")

    # 基本信息验证
    schema.add_rule(
        "property_name",
        RequiredRule(
            name="required",
            description="物业名称必填",
            required=True,
            error_message="物业名称不能为空",
        ),
    )
    schema.add_rule(
        "property_name", LengthRule(min_length=1, max_length=200, required=False)
    )

    schema.add_rule(
        "address",
        RequiredRule(
            name="required",
            description="地址必填",
            required=True,
            error_message="地址不能为空",
        ),
    )
    schema.add_rule("address", LengthRule(max_length=500, required=False))

    # 状态枚举验证
    schema.add_rule(
        "ownership_status",
        EnumRule(
            allowed_values=["已确权", "未确权", "部分确权", "无法确认业权"],
            required=False,
        ),
    )

    schema.add_rule(
        "property_nature",
        EnumRule(
            allowed_values=[
                "经营性",
                "非经营性",
                "经营-外部",
                "经营-内部",
                "经营-租赁",
                "非经营类-公配",
                "非经营类-其他",
                "经营类",
                "非经营类",
            ],
            required=False,
        ),
    )

    schema.add_rule(
        "usage_status",
        EnumRule(
            allowed_values=[
                "出租",
                "空置",
                "自用",
                "公房",
                "其他",
                "转租",
                "公配",
                "空置规划",
                "空置预留",
                "配套",
                "空置配套",
                "空置配",
                "待处置",
                "待移交",
                "闲置",
            ],
            required=False,
        ),
    )

    # 数值验证
    schema.add_rule(
        "land_area", RangeRule(min_value=0, max_value=999999.99, required=False)
    )

    schema.add_rule(
        "actual_property_area",
        RangeRule(min_value=0, max_value=999999.99, required=False),
    )

    schema.add_rule(
        "rentable_area", RangeRule(min_value=0, max_value=999999.99, required=False)
    )

    schema.add_rule(
        "rented_area", RangeRule(min_value=0, max_value=999999.99, required=False)
    )

    # 自定义验证器：出租面积不能大于可出租面积
    def validate_rented_area(value, data):
        if value is not None and data.get("rentable_area") is not None:
            if float(value) > float(data["rentable_area"]):
                raise ValueError("已出租面积不能大于可出租面积")

    schema.add_validator("rented_area", validate_rented_area)

    return schema


def create_project_validation_schema() -> ValidationSchema:
    """创建项目数据验证模式"""
    schema = ValidationSchema("project")

    schema.add_rule(
        "name", RequiredRule(name="required", description="项目名称必填", required=True)
    )
    schema.add_rule("name", LengthRule(min_length=1, max_length=200, required=False))

    schema.add_rule(
        "code", RequiredRule(name="required", description="项目编码必填", required=True)
    )
    schema.add_rule("code", LengthRule(min_length=1, max_length=100, required=False))

    return schema


# 注册预定义的验证模式
validation_framework.register_schema(create_asset_validation_schema())
validation_framework.register_schema(create_project_validation_schema())


# 装饰器：用于API端点的数据验证
def validate_data(schema_name: str):
    """数据验证装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 假设第一个参数是请求数据
            if len(args) > 0 and isinstance(args[0], dict):
                data = args[0]
                errors = validation_framework.validate(schema_name, data)
                if errors:
                    raise BusinessValidationError(errors)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# 工具函数
def validate_excel_file(file_obj) -> dict[str, list[str]]:
    """验证Excel文件"""
    errors = {}

    file_rule = FileRule(
        allowed_extensions=["xlsx", "xls"], max_size_mb=50, required=True
    )

    if not file_rule.validate(file_obj):
        errors["file"] = [file_rule.get_error_message()]

    return errors


def validate_pdf_file(file_obj) -> dict[str, list[str]]:
    """验证PDF文件"""
    errors = {}

    file_rule = FileRule(allowed_extensions=["pdf"], max_size_mb=100, required=True)

    if not file_rule.validate(file_obj):
        errors["file"] = [file_rule.get_error_message()]

    return errors


def validate_date_range(start_date: str, end_date: str) -> dict[str, list[str]]:
    """验证日期范围"""
    errors = {}

    date_rule = DateRule(date_format="%Y-%m-%d")

    if not date_rule.validate(start_date):
        errors.setdefault("start_date", []).append(date_rule.get_error_message())

    if not date_rule.validate(end_date):
        errors.setdefault("end_date", []).append(date_rule.get_error_message())

    # 验证日期逻辑
    if start_date and end_date and not errors:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                errors.setdefault("date_range", []).append("开始日期不能晚于结束日期")
        except ValueError:
            pass

    return errors
