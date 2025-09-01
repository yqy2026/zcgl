#!/usr/bin/env python3
"""
测试Excel API功能
"""

import requests
import json

def test_excel_preview():
    """测试Excel预览功能"""
    try:
        url = "http://localhost:8001/api/v1/excel/preview"
        
        with open("test_import.xlsx", "rb") as f:
            files = {"file": ("test_import.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            params = {"max_rows": 5}
            
            response = requests.post(url, files=files, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Excel预览功能测试成功")
                print(f"文件名: {data['filename']}")
                print(f"总行数: {data['total_rows']}")
                print(f"预览行数: {data['preview_rows']}")
                print(f"列名: {data['columns']}")
                print("预览数据:")
                for i, row in enumerate(data['data'], 1):
                    print(f"  第{i}行: {row}")
                return True
            else:
                print(f"❌ Excel预览失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Excel预览测试异常: {e}")
        return False

def test_excel_import():
    """测试Excel导入功能"""
    try:
        url = "http://localhost:8001/api/v1/excel/import"
        
        with open("test_import.xlsx", "rb") as f:
            files = {"file": ("test_import.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            params = {"skip_errors": True}
            
            response = requests.post(url, files=files, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Excel导入功能测试成功")
                print(f"消息: {data['message']}")
                print(f"总行数: {data['total_rows']}")
                print(f"成功导入: {data['success_count']}")
                print(f"错误数量: {data['error_count']}")
                if data['errors']:
                    print("错误信息:")
                    for error in data['errors']:
                        print(f"  {error}")
                return True
            else:
                print(f"❌ Excel导入失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Excel导入测试异常: {e}")
        return False

def test_excel_template():
    """测试Excel模板下载"""
    try:
        url = "http://localhost:8001/api/v1/excel/template"
        response = requests.get(url)
        
        if response.status_code == 200:
            with open("downloaded_template.xlsx", "wb") as f:
                f.write(response.content)
            print("✅ Excel模板下载成功")
            print(f"文件大小: {len(response.content)} 字节")
            return True
        else:
            print(f"❌ Excel模板下载失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Excel模板下载异常: {e}")
        return False

def test_excel_export():
    """测试Excel导出功能"""
    try:
        url = "http://localhost:8001/api/v1/excel/export"
        response = requests.get(url)
        
        if response.status_code == 200:
            with open("exported_data.xlsx", "wb") as f:
                f.write(response.content)
            print("✅ Excel导出功能测试成功")
            print(f"文件大小: {len(response.content)} 字节")
            return True
        else:
            print(f"❌ Excel导出失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Excel导出测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 Excel功能测试开始")
    print("=" * 50)
    
    results = []
    
    # 测试模板下载
    print("\n1. 测试Excel模板下载")
    results.append(test_excel_template())
    
    # 测试导出功能
    print("\n2. 测试Excel导出功能")
    results.append(test_excel_export())
    
    # 测试预览功能
    print("\n3. 测试Excel预览功能")
    results.append(test_excel_preview())
    
    # 测试导入功能
    print("\n4. 测试Excel导入功能")
    results.append(test_excel_import())
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    tests = ["模板下载", "数据导出", "文件预览", "数据导入"]
    for i, (test_name, result) in enumerate(zip(tests, results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {i+1}. {test_name}: {status}")
    
    success_count = sum(results)
    total_count = len(results)
    print(f"\n🎯 总体结果: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 所有Excel功能测试通过！")
    else:
        print("⚠️  部分Excel功能存在问题，请检查")

if __name__ == "__main__":
    main()