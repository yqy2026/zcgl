"""
Excel导入导出常量配置
"""

# 统一的工作簿名称
STANDARD_SHEET_NAME = "土地物业资产数据"

# Excel文件相关配置
EXCEL_CONFIG = {
    "sheet_name": STANDARD_SHEET_NAME,
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "allowed_extensions": [".xlsx", ".xls"],
    "content_types": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel"
    ]
}

# 导入配置
IMPORT_CONFIG = {
    "batch_size": 100,
    "skip_errors": False,
    "default_values": {
        "ownership_status": "未确权",
        "usage_status": "其他",
        "property_nature": "经营类"
    }
}

# 导出配置
EXPORT_CONFIG = {
    "max_records": 1000,
    "include_headers": True,
    "date_format": "%Y-%m-%d %H:%M:%S"
}