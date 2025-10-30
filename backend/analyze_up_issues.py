#!/usr/bin/env python3
# 分析类型注解升级问题
import json

def analyze_up_issues():
    """分析类型注解升级问题"""
    
    try:
        with open('ruff_errors.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 筛选UP类型的问题
    up_issues = [item for item in data if item['code'].startswith('UP')]
    
    if not up_issues:
        print("没有找到UP类型的类型注解问题")
        return
    
    print("=== 类型注解升级问题分析 ===")
    print(f"总计 {len(up_issues)} 个UP类型问题")
    
    # 按错误代码分类
    up_codes = {}
    for item in up_issues:
        code = item['code']
        if code not in up_codes:
            up_codes[code] = []
        up_codes[code].append(item)
    
    for code, issues in up_codes.items():
        print(f"\n{code}: {len(issues)} 个问题")
        print(f"描述: {issues[0]['message']}")
        
        # 显示前5个文件
        file_counts = {}
        for issue in issues:
            filename = issue['filename'].split('\\')[-1]
            file_counts[filename] = file_counts.get(filename, 0) + 1
        
        print("影响文件:")
        for filename, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {filename}: {count} 个")

if __name__ == "__main__":
    analyze_up_issues()