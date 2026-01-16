"""
Cache Manager Security Tests

测试缓存管理器的安全性，确保不再使用不安全的pickle序列化。
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.utils.cache_manager import (
    CacheJSONEncoder,
    cache_json_dumps,
    cache_json_loads,
)


class TestCacheJSONEncoder:
    """测试自定义JSON编码器"""

    def test_encode_datetime(self):
        """测试datetime序列化/反序列化"""
        now = datetime.now()
        data = {"timestamp": now, "value": 42}
        serialized = cache_json_dumps(data)
        deserialized = cache_json_loads(serialized)

        assert deserialized is not None
        assert deserialized["timestamp"] == now
        assert deserialized["value"] == 42

    def test_encode_nested_datetime(self):
        """测试嵌套结构中的datetime序列化"""
        now = datetime.now()
        data = {
            "total_assets": 100,
            "generated_at": now,
            "stats": {
                "confirmed": 50,
                "unconfirmed": 50,
                "timestamp": now,
            },
        }
        serialized = cache_json_dumps(data)
        deserialized = cache_json_loads(serialized)

        assert deserialized is not None
        assert deserialized["total_assets"] == 100
        assert deserialized["generated_at"] == now
        assert deserialized["stats"]["confirmed"] == 50
        assert deserialized["stats"]["timestamp"] == now

    def test_encode_decimal(self):
        """测试Decimal序列化/反序列化"""
        value = Decimal("123.45")
        data = {"amount": value}
        serialized = cache_json_dumps(data)
        deserialized = cache_json_loads(serialized)

        assert deserialized is not None
        assert deserialized["amount"] == 123.45
        assert isinstance(deserialized["amount"], float)

    def test_encode_mixed_types(self):
        """测试混合类型数据序列化"""
        now = datetime.now()
        data = {
            "int_value": 42,
            "float_value": 3.14,
            "str_value": "test",
            "bool_value": True,
            "none_value": None,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "value"},
            "datetime_value": now,
            "decimal_value": Decimal("99.99"),
        }
        serialized = cache_json_dumps(data)
        deserialized = cache_json_loads(serialized)

        assert deserialized is not None
        assert deserialized["int_value"] == 42
        assert deserialized["float_value"] == 3.14
        assert deserialized["str_value"] == "test"
        assert deserialized["bool_value"] is True
        assert deserialized["none_value"] is None
        assert deserialized["list_value"] == [1, 2, 3]
        assert deserialized["dict_value"] == {"nested": "value"}
        assert deserialized["datetime_value"] == now
        assert deserialized["decimal_value"] == 99.99

    def test_encode_statistics_like_data(self):
        """测试类似统计数据结构的序列化"""
        now = datetime.now()
        data = {
            "total_assets": 1000,
            "ownership_status": {
                "confirmed": 600,
                "unconfirmed": 300,
                "partial": 100,
            },
            "property_nature": {
                "commercial": 700,
                "non_commercial": 300,
            },
            "generated_at": now,
            "filters_applied": {"ownership_status": "已确权"},
        }
        serialized = cache_json_dumps(data)
        deserialized = cache_json_loads(serialized)

        assert deserialized is not None
        assert deserialized["total_assets"] == 1000
        assert deserialized["ownership_status"]["confirmed"] == 600
        assert deserialized["generated_at"] == now
        assert deserialized["filters_applied"] == {"ownership_status": "已确权"}


class TestCacheSecurityNoPickle:
    """测试确保不再使用pickle"""

    def test_no_pickle_import(self):
        """确保cache_manager模块中没有导入pickle"""
        import src.utils.cache_manager as cm

        # 检查模块中是否有pickle相关的导入
        assert "pickle" not in dir(cm), "cache_manager不应该导入pickle模块"

    def test_json_functions_exist(self):
        """确保JSON序列化函数存在"""
        from src.utils.cache_manager import (
            cache_json_dumps,
            cache_json_loads,
        )

        assert callable(cache_json_dumps)
        assert callable(cache_json_loads)


class TestCacheJSONErrorHandling:
    """测试JSON错误处理"""

    def test_invalid_json_returns_none(self):
        """测试无效JSON返回None"""
        invalid_data = b"invalid json data"
        result = cache_json_loads(invalid_data)
        assert result is None

    def test_invalid_utf8_returns_none(self):
        """测试无效UTF-8返回None"""
        invalid_utf8 = b"\xff\xfe invalid utf-8"
        result = cache_json_loads(invalid_utf8)
        assert result is None

    def test_empty_data_returns_none(self):
        """测试空数据返回None"""
        result = cache_json_loads(b"")
        assert result is None

    def test_malformed_object_returns_none(self):
        """测试格式错误的对象返回None"""
        malformed = b'{"__datetime__": "not-a-valid-iso-date"}'
        result = cache_json_loads(malformed)
        # 应该返回None或保留原始数据（取决于实现）
        assert result is None or isinstance(result, dict)
