"""
资产批量操作验证器单元测试

测试 AssetBatchValidator 的数据验证逻辑
"""

from src.services.asset.validators import AssetBatchValidator


# ============================================================================
# validate_required_fields 测试
# ============================================================================
class TestValidateRequiredFields:
    """测试必填字段验证"""

    def test_all_required_fields_present(self):
        """测试所有必填字段都存在"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
        }
        errors = AssetBatchValidator.validate_required_fields(data)
        assert len(errors) == 0

    def test_missing_one_required_field(self):
        """测试缺少一个必填字段"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            # 缺少 usage_status
        }
        errors = AssetBatchValidator.validate_required_fields(data)
        assert len(errors) == 1
        assert errors[0]["field"] == "usage_status"
        assert "必填字段" in errors[0]["error"]

    def test_missing_all_required_fields(self):
        """测试缺少所有必填字段"""
        data = {}
        errors = AssetBatchValidator.validate_required_fields(data)
        assert len(errors) == 5

    def test_empty_string_treated_as_missing(self):
        """测试空字符串视为缺失"""
        data = {
            "property_name": "",  # 空字符串
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
        }
        errors = AssetBatchValidator.validate_required_fields(data)
        assert len(errors) == 1
        assert errors[0]["field"] == "property_name"

    def test_none_treated_as_missing(self):
        """测试 None 视为缺失"""
        data = {
            "property_name": None,
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
        }
        errors = AssetBatchValidator.validate_required_fields(data)
        assert len(errors) == 1
        assert errors[0]["field"] == "property_name"

    def test_zero_accepted_for_non_required_fields(self):
        """测试非必填字段接受 0"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "monthly_rent": 0,  # 0 是有效值
        }
        errors = AssetBatchValidator.validate_required_fields(data)
        assert len(errors) == 0


# ============================================================================
# validate_numeric_fields 测试
# ============================================================================
class TestValidateNumericFields:
    """测试数值字段验证"""

    def test_all_numeric_fields_valid(self):
        """测试所有数值字段都有效"""
        data = {
            "land_area": 100.5,
            "actual_property_area": 200.0,
            "rentable_area": 150.0,
            "rented_area": 100.0,
            "annual_income": 50000.0,
            "annual_expense": 10000.0,
            "monthly_rent": 5000.0,
            "deposit": 15000.0,
        }
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 0

    def test_numeric_fields_as_strings(self):
        """测试数值字段以字符串形式提供"""
        data = {"land_area": "100.5", "monthly_rent": "5000"}
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 0

    def test_invalid_numeric_field_string(self):
        """测试无效的数值字符串"""
        data = {"land_area": "not a number"}
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 1
        assert errors[0]["field"] == "land_area"
        assert "必须是有效的数字" in errors[0]["error"]

    def test_none_numeric_field_skipped(self):
        """测试 None 数值字段被跳过"""
        data = {"land_area": None, "monthly_rent": None}
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 0

    def test_missing_numeric_field_skipped(self):
        """测试缺失的数值字段被跳过"""
        data = {}
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 0

    def test_negative_numbers_accepted(self):
        """测试负数被接受"""
        data = {"annual_income": -5000.0}
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 0  # 业务逻辑上允许负数（亏损）

    def test_zero_accepted(self):
        """测试 0 被接受"""
        data = {"monthly_rent": 0}
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 0

    def test_scientific_notation_accepted(self):
        """测试科学计数法被接受"""
        data = {"land_area": "1.5e2"}  # 150
        errors = AssetBatchValidator.validate_numeric_fields(data)
        assert len(errors) == 0


# ============================================================================
# validate_date_fields 测试
# ============================================================================
class TestValidateDateFields:
    """测试日期字段验证"""

    def test_all_date_fields_valid(self):
        """测试所有日期字段都有效"""
        data = {
            "contract_start_date": "2024-01-01",
            "contract_end_date": "2024-12-31",
            "operation_agreement_start_date": "2024-01-01",
            "operation_agreement_end_date": "2024-12-31",
        }
        errors = AssetBatchValidator.validate_date_fields(data)
        assert len(errors) == 0

    def test_invalid_date_format(self):
        """测试无效的日期格式"""
        data = {"contract_start_date": "2024/01/01"}  # 错误格式
        errors = AssetBatchValidator.validate_date_fields(data)
        assert len(errors) == 1
        assert errors[0]["field"] == "contract_start_date"
        assert "YYYY-MM-DD" in errors[0]["error"]

    def test_none_date_skipped(self):
        """测试 None 日期被跳过"""
        data = {"contract_start_date": None}
        errors = AssetBatchValidator.validate_date_fields(data)
        assert len(errors) == 0

    def test_missing_date_skipped(self):
        """测试缺失的日期被跳过"""
        data = {}
        errors = AssetBatchValidator.validate_date_fields(data)
        assert len(errors) == 0

    def test_empty_string_fails_validation(self):
        """测试空字符串验证失败"""
        data = {"contract_start_date": ""}
        errors = AssetBatchValidator.validate_date_fields(data)
        assert len(errors) == 1

    def test_partial_date_format(self):
        """测试不完整的日期格式"""
        data = {"contract_start_date": "2024-01"}  # 只有年月
        errors = AssetBatchValidator.validate_date_fields(data)
        assert len(errors) == 1

    def test_non_string_type_skipped(self):
        """测试非字符串类型被跳过"""
        data = {"contract_start_date": 20240101}  # 整数
        errors = AssetBatchValidator.validate_date_fields(data)
        assert len(errors) == 0


# ============================================================================
# validate_area_consistency 测试
# ============================================================================
class TestValidateAreaConsistency:
    """测试面积一致性验证"""

    def test_consistent_areas(self):
        """测试一致的面积"""
        data = {"rentable_area": 100.0, "rented_area": 50.0}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_equal_areas(self):
        """测试相等面积（边界情况）"""
        data = {"rentable_area": 100.0, "rented_area": 100.0}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_rented_exceeds_rentable(self):
        """测试已出租面积大于可出租面积"""
        data = {"rentable_area": 100.0, "rented_area": 150.0}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 1
        assert errors[0]["field"] == "rented_area"
        assert "已出租面积不能大于可出租面积" in errors[0]["error"]

    def test_missing_rentable_area(self):
        """测试缺少可出租面积"""
        data = {"rented_area": 50.0}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_missing_rented_area(self):
        """测试缺少已出租面积"""
        data = {"rentable_area": 100.0}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_both_missing(self):
        """测试两者都缺失"""
        data = {}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_string_areas_converted(self):
        """测试字符串面积被转换"""
        data = {"rentable_area": "100.0", "rented_area": "50.0"}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_invalid_string_areas_skipped(self):
        """测试无效字符串面积（无法转换）被跳过"""
        data = {"rentable_area": "invalid", "rented_area": "50.0"}
        errors = AssetBatchValidator.validate_area_consistency(data)
        assert len(errors) == 0  # 类型转换失败，跳过验证


# ============================================================================
# get_suggestion_warnings 测试
# ============================================================================
class TestGetSuggestionWarnings:
    """测试建议性警告"""

    def test_no_suggestions_for_complete_data(self):
        """测试完整数据无建议"""
        data = {
            "land_area": 100.0,
            "annual_income": 50000.0,
            "annual_expense": 10000.0,
            "tenant_name": "张三公司",
        }
        warnings = AssetBatchValidator.get_suggestion_warnings(data)
        assert len(warnings) == 0

    def test_suggestion_for_missing_land_area(self):
        """测试缺少土地面积时的建议"""
        data = {}
        warnings = AssetBatchValidator.get_suggestion_warnings(data)
        land_warnings = [w for w in warnings if w["field"] == "land_area"]
        assert len(land_warnings) == 1
        assert "土地面积" in land_warnings[0]["message"]

    def test_suggestion_for_missing_annual_income(self):
        """测试缺少年收入时的建议"""
        data = {}
        warnings = AssetBatchValidator.get_suggestion_warnings(data)
        income_warnings = [w for w in warnings if w["field"] == "annual_income"]
        assert len(income_warnings) == 1
        assert "年收入" in income_warnings[0]["message"]

    def test_suggestion_for_missing_tenant_name(self):
        """测试缺少租户信息时的建议"""
        data = {}
        warnings = AssetBatchValidator.get_suggestion_warnings(data)
        tenant_warnings = [w for w in warnings if w["field"] == "tenant_name"]
        assert len(tenant_warnings) == 1
        assert "租户信息" in tenant_warnings[0]["message"]

    def test_none_values_trigger_suggestions(self):
        """测试 None 值触发建议"""
        data = {"land_area": None}
        warnings = AssetBatchValidator.get_suggestion_warnings(data)
        # land_area is None but is in data, so it triggers a warning
        # Plus the other 3 fields that are missing
        assert len(warnings) == 4

    def test_zero_values_do_not_trigger_suggestions(self):
        """测试 0 值不触发建议（0 是有效值）"""
        data = {
            "land_area": 0,
            "annual_income": 0,
            "annual_expense": 0,
            "tenant_name": "张三",
        }
        warnings = AssetBatchValidator.get_suggestion_warnings(data)
        # All suggestion fields are present (even if 0), so no warnings
        assert len(warnings) == 0


# ============================================================================
# validate_all 测试
# ============================================================================
class TestValidateAll:
    """测试完整验证流程"""

    def test_valid_data_returns_valid(self):
        """测试有效数据返回验证通过"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "land_area": 100.0,
            # Add all suggestion fields to avoid warnings
            "annual_income": 0,
            "annual_expense": 0,
            "tenant_name": "测试租户",
        }
        is_valid, errors, warnings, validated_fields = AssetBatchValidator.validate_all(
            data
        )

        assert is_valid is True
        assert len(errors) == 0
        assert len(warnings) == 0  # All suggestion fields present
        # validated_fields includes 5 required fields + 3 numeric fields (land_area, annual_income, annual_expense)
        # tenant_name is not tracked in validated_fields
        assert len(validated_fields) == 8

    def test_missing_required_field_returns_invalid(self):
        """测试缺少必填字段返回验证失败"""
        data = {
            "property_name": "测试物业",
            # 缺少其他必填字段
        }
        is_valid, errors, warnings, validated_fields = AssetBatchValidator.validate_all(
            data
        )

        assert is_valid is False
        assert len(errors) == 4
        assert len(validated_fields) == 1

    def test_invalid_numeric_format_returns_error(self):
        """测试无效数值格式返回错误"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "land_area": "invalid",  # 无效数值
        }
        is_valid, errors, warnings, validated_fields = AssetBatchValidator.validate_all(
            data
        )

        assert is_valid is False
        assert any(e["field"] == "land_area" for e in errors)

    def test_custom_validation_rules(self):
        """测试自定义验证规则"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "rentable_area": 100.0,
            "rented_area": 150.0,  # 不一致
        }
        # 只验证面积一致性，不验证必填字段
        is_valid, errors, warnings, validated_fields = AssetBatchValidator.validate_all(
            data, validate_rules=["data_format"]
        )

        # 面积一致性应该被验证
        assert any("已出租面积不能大于可出租面积" in e["error"] for e in errors)

    def test_validated_fields_list(self):
        """测试已验证字段列表"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "land_area": 100.0,
            "contract_start_date": "2024-01-01",
            "rentable_area": 100.0,
            "rented_area": 50.0,
        }
        is_valid, errors, warnings, validated_fields = AssetBatchValidator.validate_all(
            data
        )

        # 应该包含所有通过验证的字段
        assert "property_name" in validated_fields
        assert "address" in validated_fields
        assert "land_area" in validated_fields
        assert "contract_start_date" in validated_fields
        assert "rentable_area" in validated_fields
        assert "rented_area" in validated_fields

    def test_empty_validate_rules(self):
        """测试空验证规则列表（会使用默认规则）"""
        data = {}
        is_valid, errors, warnings, validated_fields = AssetBatchValidator.validate_all(
            data, validate_rules=[]
        )

        # Empty list triggers default validation rules
        assert is_valid is False  # Missing required fields
        assert len(errors) == 5  # All 5 required fields missing
        assert len(validated_fields) == 0
        # 建议性警告仍然存在
        assert len(warnings) == 4
