#!/usr/bin/env python3
"""
测试Excel功能
"""

import pandas as pd
import io

def test_excel_creation():
    """测试Excel文件创建"""
    try:
        # 创建示例数据
        template_data = {
            "物业名称": ["示例物业1", "示例物业2"],
            "地址": ["示例地址1", "示例地址2"],
            "确权状态": ["已确权", "未确权"],
            "物业性质": ["经营性", "非经营性"],
            "使用状态": ["出租", "自用"],
            "权属方": ["示例权属方1", "示例权属方2"],
            "经营管理方": ["示例管理方1", "示例管理方2"],
            "业态类别": ["商业", "办公"],
            "总面积": [1000.0, 2000.0],
            "可使用面积": [800.0, 1800.0],
            "是否涉诉": ["否", "否"],
            "备注": ["示例备注1", "示例备注2"]
        }
        
        # 创建DataFrame
        df = pd.DataFrame(template_data)
        print("✅ DataFrame创建成功")
        print(f"数据形状: {df.shape}")
        print(f"列名: {list(df.columns)}")
        
        # 写入Excel文件
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="资产导入模板", index=False)
        
        print("✅ Excel文件创建成功")
        print(f"文件大小: {len(buffer.getvalue())} 字节")
        
        # 保存到文件
        with open("test_template.xlsx", "wb") as f:
            f.write(buffer.getvalue())
        
        print("✅ 文件保存成功: test_template.xlsx")
        
        return True
        
    except Exception as e:
        print(f"❌ Excel创建失败: {e}")
        return False

if __name__ == "__main__":
    test_excel_creation()