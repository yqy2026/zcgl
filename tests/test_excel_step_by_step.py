#!/usr/bin/env python3
"""
逐步测试Excel功能
"""

import requests
import json
import pandas as pd
import io

def test_basic_connection():
    """测试基本连接"""
    try:
        response = requests.get("http://localhost:8001/")
        if response.status_code == 200:
            print("✅ 后端连接正常")
            return True
        else:
            print(f"❌ 后端连接异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        return False

def test_excel_template():
    """测试Excel模板下载"""
    try:
        print("\n🧪 测试Excel模板下载...")
        response = requests.get("http://localhost:8001/api/v1/excel/template")
        
        if response.status_code == 200:
            print("✅ 模板下载成功")
            print(f"   文件大小: {len(response.content)} 字节")
            
            # 保存并验证文件
            with open("test_template_download.xlsx", "wb") as f:
                f.write(response.content)
            
            # 验证文件可读性
            df = pd.read_excel("test_template_download.xlsx")
            print(f"   数据行数: {len(df)}")
            print(f"   列数: {len(df.columns)}")
            print(f"   列名: {list(df.columns)}")
            return True
        else:
            print(f"❌ 模板下载失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 模板下载测试异常: {e}")
        return False

def test_excel_export():
    """测试Excel导出"""
    try:
        print("\n🧪 测试Excel导出...")
        response = requests.get("http://localhost:8001/api/v1/excel/export")
        
        if response.status_code == 200:
            print("✅ 数据导出成功")
            print(f"   文件大小: {len(response.content)} 字节")
            
            # 保存并验证文件
            with open("test_export_download.xlsx", "wb") as f:
                f.write(response.content)
            
            # 验证文件可读性
            df = pd.read_excel("test_export_download.xlsx")
            print(f"   数据行数: {len(df)}")
            print(f"   列数: {len(df.columns)}")
            return True
        else:
            print(f"❌ 数据导出失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 数据导出测试异常: {e}")
        return False

def create_test_excel():
    """创建测试Excel文件"""
    try:
        print("\n📝 创建测试Excel文件...")
        test_data = {
            "物业名称": ["测试物业A", "测试物业B"],
            "地址": ["北京市朝阳区测试路1号", "上海市浦东新区测试路2号"],
            "确权状态": ["已确权", "未确权"],
            "物业性质": ["经营性", "经营性"],
            "使用状态": ["出租", "自用"],
            "权属方": ["国有", "集体"],
            "经营管理方": ["测试管理公司A", "测试管理公司B"],
            "业态类别": ["办公", "商业"],
            "总面积": [1500.0, 2500.0],
            "可使用面积": [1200.0, 2200.0],
            "是否涉诉": ["否", "否"],
            "备注": ["测试数据A", "测试数据B"]
        }
        
        df = pd.DataFrame(test_data)
        df.to_excel("test_for_preview.xlsx", sheet_name="测试数据", index=False)
        print("✅ 测试Excel文件创建成功")
        print(f"   文件: test_for_preview.xlsx")
        print(f"   数据行数: {len(df)}")
        return True
    except Exception as e:
        print(f"❌ 创建测试文件失败: {e}")
        return False

def test_excel_preview():
    """测试Excel预览功能"""
    try:
        print("\n🧪 测试Excel预览功能...")
        
        # 确保测试文件存在
        if not create_test_excel():
            return False
        
        url = "http://localhost:8001/api/v1/excel/preview"
        
        with open("test_for_preview.xlsx", "rb") as f:
            files = {
                "file": ("test_for_preview.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            }
            params = {"max_rows": 5}
            
            print("   发送预览请求...")
            response = requests.post(url, files=files, params=params)
            
            print(f"   响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Excel预览成功")
                print(f"   文件名: {data['filename']}")
                print(f"   总行数: {data['total_rows']}")
                print(f"   预览行数: {data['preview_rows']}")
                print(f"   列数: {len(data['columns'])}")
                print(f"   列名: {data['columns']}")
                
                if data['data']:
                    print("   预览数据:")
                    for i, row in enumerate(data['data'], 1):
                        print(f"     第{i}行: {row}")
                
                return True
            else:
                print(f"❌ Excel预览失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                
                # 尝试解析错误信息
                try:
                    error_data = response.json()
                    print(f"   详细错误: {error_data}")
                except:
                    pass
                
                return False
                
    except Exception as e:
        print(f"❌ Excel预览测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_excel_import():
    """测试Excel导入功能"""
    try:
        print("\n🧪 测试Excel导入功能...")
        
        url = "http://localhost:8001/api/v1/excel/import"
        
        with open("test_for_preview.xlsx", "rb") as f:
            files = {
                "file": ("test_for_preview.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            }
            params = {"skip_errors": True}
            
            print("   发送导入请求...")
            response = requests.post(url, files=files, params=params)
            
            print(f"   响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Excel导入成功")
                print(f"   消息: {data['message']}")
                print(f"   总行数: {data['total_rows']}")
                print(f"   成功导入: {data['success_count']}")
                print(f"   错误数量: {data['error_count']}")
                
                if data['errors']:
                    print("   错误信息:")
                    for error in data['errors']:
                        print(f"     {error}")
                
                return True
            else:
                print(f"❌ Excel导入失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Excel导入测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 Excel功能逐步排查测试")
    print("=" * 60)
    
    # 测试步骤
    steps = [
        ("基本连接", test_basic_connection),
        ("Excel模板下载", test_excel_template),
        ("Excel数据导出", test_excel_export),
        ("Excel文件预览", test_excel_preview),
        ("Excel数据导入", test_excel_import),
    ]
    
    results = []
    
    for step_name, test_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        result = test_func()
        results.append((step_name, result))
        
        if not result:
            print(f"\n⚠️  {step_name} 失败，继续下一个测试...")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    for step_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {step_name}: {status}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    print(f"\n🎯 总体结果: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 所有Excel功能测试通过！")
    else:
        print("⚠️  部分Excel功能存在问题")
        
        # 给出具体建议
        failed_tests = [name for name, result in results if not result]
        print(f"\n❌ 失败的测试: {', '.join(failed_tests)}")

if __name__ == "__main__":
    main()