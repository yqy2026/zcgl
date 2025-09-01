#!/usr/bin/env python3
"""
调试Excel预览功能
"""

import pandas as pd
import tempfile
import io

def debug_excel_read():
    """调试Excel读取"""
    try:
        # 读取测试文件
        print("📖 读取Excel文件...")
        df = pd.read_excel("test_import.xlsx")
        print(f"✅ 文件读取成功")
        print(f"数据形状: {df.shape}")
        print(f"列名: {list(df.columns)}")
        print(f"数据类型: {df.dtypes}")
        
        # 测试转换为字典
        print("\n🔄 转换为字典格式...")
        records = df.to_dict('records')
        print(f"✅ 转换成功，记录数: {len(records)}")
        
        # 显示第一条记录
        if records:
            print(f"第一条记录: {records[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_temp_file():
    """调试临时文件处理"""
    try:
        print("📁 测试临时文件处理...")
        
        # 读取原文件
        with open("test_import.xlsx", "rb") as f:
            content = f.read()
        
        print(f"原文件大小: {len(content)} 字节")
        
        # 使用临时文件
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=True) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            print(f"临时文件路径: {tmp_file.name}")
            
            # 读取Excel
            df = pd.read_excel(tmp_file.name)
            print(f"✅ 临时文件读取成功")
            print(f"数据形状: {df.shape}")
            
        return True
        
    except Exception as e:
        print(f"❌ 临时文件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Excel预览功能调试")
    print("=" * 40)
    
    print("\n1. 直接读取Excel文件")
    debug_excel_read()
    
    print("\n2. 临时文件处理测试")
    debug_temp_file()