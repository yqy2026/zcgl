#!/usr/bin/env python3
# 分析编码和格式问题
import json

def analyze_formatting_issues():
    """分析编码和格式问题"""
    
    try:
        with open('ruff_errors.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 筛选格式化和编码问题
    formatting_codes = ['W293', 'W291', 'W292', 'W505', 'W191']
    formatting_issues = [item for item in data if item['code'] in formatting_codes]
    
    # 其他常见的格式问题
    other_formatting = ['E122', 'E127', 'E128', 'E203', 'E211', 'E221', 'E222', 'E223', 'E224', 'E225', 'E226', 'E227', 'E228', 'E231', 'E251', 'E261', 'E262', 'E265', 'E266', 'E271', 'E272', 'E273', 'E274', 'E275']
    other_issues = [item for item in data if item['code'] in other_formatting]
    
    print("=== 编码和格式问题分析 ===")
    
    if formatting_issues:
        print(f"空白符和编码问题: {len(formatting_issues)} 个")
        file_counts = {}
        for issue in formatting_issues:
            filename = issue['filename'].split('\\')[-1]
            file_counts[filename] = file_counts.get(filename, 0) + 1
        
        print("主要影响文件:")
        for filename, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {filename}: {count} 个")
    
    if other_issues:
        print(f"\n其他格式问题: {len(other_issues)} 个")
        file_counts = {}
        for issue in other_issues:
            filename = issue['filename'].split('\\')[-1]
            file_counts[filename] = file_counts.get(filename, 0) + 1
        
        print("主要影响文件:")
        for filename, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {filename}: {count} 个")
    
    # 分析最严重的格式问题
    w293_issues = [item for item in data if item['code'] == 'W293']
    w291_issues = [item for item in data if item['code'] == 'W291']
    w292_issues = [item for item in data if item['code'] == 'W292']
    
    print(f"\n详细统计:")
    print(f"  W293 (空白行包含空白符): {len(w293_issues)} 个")
    print(f"  W291 (行尾空白符): {len(w291_issues)} 个") 
    print(f"  W292 (文件末尾缺少换行符): {len(w292_issues)} 个")
    
    if w293_issues:
        print("\n  W293问题最多的文件:")
        file_counts = {}
        for issue in w293_issues[:20]:  # 前20个
            filename = issue['filename'].split('\\')[-1]
            file_counts[filename] = file_counts.get(filename, 0) + 1
        
        for filename, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {filename}: {count} 个")

if __name__ == "__main__":
    analyze_formatting_issues()