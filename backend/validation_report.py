#!/usr/bin/env python3
"""
代码质量修复验证报告
"""

import ast
import os
import sys
from pathlib import Path

def check_syntax_errors(file_path):
    """检查文件语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def analyze_file(file_path):
    """分析单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        stats = {
            'lines': len(content.splitlines()),
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'errors': []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                stats['functions'] += 1
            elif isinstance(node, ast.ClassDef):
                stats['classes'] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                stats['imports'] += 1
        
        return stats
    except Exception as e:
        return {'lines': 0, 'functions': 0, 'classes': 0, 'imports': 0, 'errors': [str(e)]}

def main():
    """主函数"""
    print("=" * 80)
    print("代码质量修复验证报告")
    print("=" * 80)
    
    src_dir = Path(__file__).parent / "src"
    
    if not src_dir.exists():
        print(f"❌ 源目录不存在: {src_dir}")
        return 1
    
    # 关键文件列表
    key_files = [
        "main.py",
        "database.py", 
        "models/asset.py",
        "schemas/asset.py",
        "api/v1/assets.py",
        "services/pdf_processing_service.py",
        "core/config_manager.py",
        "middleware/auth.py"
    ]
    
    total_files = 0
    total_lines = 0
    total_functions = 0
    total_classes = 0
    syntax_errors = 0
    
    print("\n🔍 检查关键文件语法...")
    
    for file_path in key_files:
        full_path = src_dir / file_path
        if full_path.exists():
            is_valid, error = check_syntax_errors(full_path)
            if is_valid:
                print(f"✅ {file_path} - 语法正确")
                stats = analyze_file(full_path)
                total_files += 1
                total_lines += stats['lines']
                total_functions += stats['functions']
                total_classes += stats['classes']
            else:
                print(f"❌ {file_path} - 语法错误: {error}")
                syntax_errors += 1
        else:
            print(f"⚠️  {file_path} - 文件不存在")
    
    print(f"\n📊 代码统计:")
    print(f"   检查文件数: {total_files}")
    print(f"   总行数: {total_lines}")
    print(f"   总函数数: {total_functions}")
    print(f"   总类数: {total_classes}")
    print(f"   语法错误: {syntax_errors}")
    
    print(f"\n🔍 检查所有Python文件...")
    
    # 检查所有Python文件
    all_python_files = list(src_dir.rglob("*.py"))
    syntax_error_files = []
    
    for py_file in all_python_files:
        is_valid, error = check_syntax_errors(py_file)
        if not is_valid:
            syntax_error_files.append((py_file.relative_to(src_dir), error))
    
    print(f"   总Python文件数: {len(all_python_files)}")
    print(f"   语法错误文件数: {len(syntax_error_files)}")
    
    if syntax_error_files:
        print(f"\n❌ 语法错误文件列表:")
        for file_path, error in syntax_error_files:
            print(f"   {file_path}: {error}")
    
    # 检查基本导入
    print(f"\n🔍 测试基本导入...")
    try:
        sys.path.insert(0, str(src_dir))
        
        # 测试核心模块导入
        modules_to_test = [
            "main",
            "database", 
            "models.asset",
            "schemas.asset",
            "api.v1.assets"
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                print(f"✅ {module_name} - 导入成功")
            except Exception as e:
                print(f"❌ {module_name} - 导入失败: {e}")
        
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
    
    print("\n" + "=" * 80)
    
    if syntax_errors == 0 and len(syntax_error_files) == 0:
        print("🎉 恭喜！所有代码质量修复验证通过")
        print("✅ 没有发现语法错误")
        print("✅ 基本模块导入正常")
        return 0
    else:
        print("⚠️  发现一些问题需要修复:")
        if syntax_errors > 0:
            print(f"   - {syntax_errors}个关键文件有语法错误")
        if len(syntax_error_files) > 0:
            print(f"   - {len(syntax_error_files)}个Python文件有语法错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())