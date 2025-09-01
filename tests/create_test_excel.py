#!/usr/bin/env python3
"""
创建测试用的Excel文件
"""

import pandas as pd

def create_test_excel():
    """创建测试Excel文件"""
    test_data = {
        "物业名称": ["测试物业A", "测试物业B", "测试物业C"],
        "地址": ["北京市朝阳区测试路1号", "上海市浦东新区测试路2号", "广州市天河区测试路3号"],
        "确权状态": ["已确权", "未确权", "已确权"],
        "物业性质": ["经营性", "经营性", "非经营性"],
        "使用状态": ["出租", "自用", "空置"],
        "权属方": ["国有", "集体", "私有"],
        "经营管理方": ["测试管理公司A", "测试管理公司B", "测试管理公司C"],
        "业态类别": ["办公", "商业", "住宅"],
        "总面积": [1500.0, 2500.0, 800.0],
        "可使用面积": [1200.0, 2200.0, 700.0],
        "是否涉诉": ["否", "是", "否"],
        "备注": ["测试数据A", "测试数据B", "测试数据C"]
    }
    
    df = pd.DataFrame(test_data)
    df.to_excel("test_import.xlsx", sheet_name="测试数据", index=False)
    print("✅ 测试Excel文件创建成功: test_import.xlsx")
    print(f"数据行数: {len(df)}")
    print(f"列数: {len(df.columns)}")

if __name__ == "__main__":
    create_test_excel()