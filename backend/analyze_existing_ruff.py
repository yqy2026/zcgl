#!/usr/bin/env python3
# 分析现有的ruff错误文件
import json
from collections import defaultdict
import os

def analyze_ruff_errors():
    """分析ruff错误文件"""
    
    # 读取现有的ruff错误文件
    try:
        with open('ruff_errors.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取ruff_errors.json失败: {e}")
        return
    
    # 统计数据
    error_counts = defaultdict(int)
    file_counts = defaultdict(int)
    severity_mapping = {
        'F821': 'HIGH',  # 未定义名称 - 严重
        'F401': 'HIGH',  # 未使用导入 - 高
        'F841': 'MEDIUM', # 未使用变量 - 中
        'E712': 'MEDIUM', # 布尔值比较 - 中
        'E402': 'LOW',    # 导入位置 - 低
        'W292': 'LOW',    # 文件结尾 - 低
        'UP006': 'LOW',   # 类型注解 - 低
        'UP045': 'LOW',   # 类型注解 - 低
        'E721': 'MEDIUM', # 类型比较 - 中
        'F811': 'MEDIUM', # 重定义 - 中
        'F823': 'HIGH',   # 未定义局部变量 - 高
        'N818': 'LOW',    # 命名规范 - 低
        'UP009': 'LOW',   # UTF8声明 - 低
        'UP035': 'LOW',   # 废弃导入 - 低
        'UP046': 'LOW',   # 泛型 - 低
    }
    
    severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    
    for item in data:
        code = item['code']
        filename = item['filename']
        
        error_counts[code] += 1
        file_counts[filename] += 1
        
        severity = severity_mapping.get(code, 'LOW')
        severity_counts[severity] += 1
    
    # 输出分析报告
    print("=== BACKEND代码质量问题深度分析报告 ===\n")
    
    print("1. 问题总数统计:")
    print(f"   总问题数: {len(data)}")
    print(f"   问题类型数: {len(error_counts)}")
    print(f"   影响文件数: {len(file_counts)}")
    
    print(f"\n2. 严重程度分布:")
    for severity, count in severity_counts.items():
        percentage = (count / len(data)) * 100 if len(data) > 0 else 0
        print(f"   {severity}: {count} ({percentage:.1f}%)")
    
    print(f"\n3. 主要问题类型 (前15个):")
    for code, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
        severity = severity_mapping.get(code, 'LOW')
        percentage = (count / len(data)) * 100
        print(f"   {code}: {count} ({percentage:.1f}%) - {severity}")
    
    print(f"\n4. 问题最严重的文件 (前20个):")
    for filename, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"   {os.path.basename(filename)}: {count} 个问题")
    
    print(f"\n5. 关键问题详细分析:")
    
    # F821 未定义名称 (最高优先级)
    f821_issues = [item for item in data if item['code'] == 'F821']
    if f821_issues:
        print(f"\n   5.1 F821 未定义名称 ({len(f821_issues)} 个) - 必须立即修复:")
        file_groups = defaultdict(list)
        for item in f821_issues:
            file_groups[item['filename']].append(item)
        
        for filename, issues in list(file_groups.items())[:10]:  # 显示前10个文件
            print(f"       {os.path.basename(filename)}: {len(issues)} 个")
            for issue in issues[:3]:  # 每个文件显示前3个
                print(f"         行 {issue['location']['row']}: {issue['message']}")
    
    # F401 未使用导入
    f401_issues = [item for item in data if item['code'] == 'F401']
    if f401_issues:
        print(f"\n   5.2 F401 未使用导入 ({len(f401_issues)} 个) - 高优先级:")
        file_groups = defaultdict(list)
        for item in f401_issues:
            file_groups[item['filename']].append(item)
        
        for filename, issues in list(file_groups.items())[:5]:
            print(f"       {os.path.basename(filename)}: {len(issues)} 个")
    
    # F841 未使用变量
    f841_issues = [item for item in data if item['code'] == 'F841']
    if f841_issues:
        print(f"\n   5.3 F841 未使用变量 ({len(f841_issues)} 个) - 中等优先级:")
        file_groups = defaultdict(list)
        for item in f841_issues:
            file_groups[item['filename']].append(item)
        
        for filename, issues in list(file_groups.items())[:5]:
            print(f"       {os.path.basename(filename)}: {len(issues)} 个")
    
    # E712 布尔值比较
    e712_issues = [item for item in data if item['code'] == 'E712']
    if e712_issues:
        print(f"\n   5.4 E712 布尔值比较 ({len(e712_issues)} 个) - 代码风格:")
        file_groups = defaultdict(list)
        for item in e712_issues:
            file_groups[item['filename']].append(item)
        
        for filename, issues in list(file_groups.items())[:5]:
            print(f"       {os.path.basename(filename)}: {len(issues)} 个")
    
    print(f"\n6. 修复建议和优先级:")
    print("   第一优先级 (立即修复):")
    print("   - F821 未定义名称: 这些是运行时错误，必须立即修复")
    print("   - F823 未定义局部变量: 可能导致运行时错误")
    print("   - F811 重定义未使用: 可能导致逻辑错误")
    
    print("\n   第二优先级 (近期修复):")
    print("   - F401 未使用导入: 清理代码，减少依赖")
    print("   - F841 未使用变量: 清理无用代码")
    
    print("\n   第三优先级 (逐步优化):")
    print("   - E712 布尔值比较: 代码风格优化")
    print("   - E402 导入位置: 代码结构优化")
    print("   - UP类型问题: 类型注解现代化")
    
    print(f"\n7. 预估修复工作量:")
    high_priority = severity_counts['HIGH']
    medium_priority = severity_counts['MEDIUM']
    low_priority = severity_counts['LOW']
    
    print(f"   高优先级问题: {high_priority} 个 - 预计 {high_priority * 0.5} 小时")
    print(f"   中优先级问题: {medium_priority} 个 - 预计 {medium_priority * 0.3} 小时") 
    print(f"   低优先级问题: {low_priority} 个 - 预计 {low_priority * 0.1} 小时")
    print(f"   总计: {high_priority * 0.5 + medium_priority * 0.3 + low_priority * 0.1:.1f} 小时")
    
    print(f"\n8. 代码质量趋势:")
    if len(data) > 1000:
        print("   代码质量需要显著改善 - 问题数量过多")
    elif len(data) > 500:
        print("   代码质量有待改善 - 存在一定数量的问题")
    else:
        print("   代码质量相对较好 - 问题数量可控")
    
    print(f"\n=== 报告完成 ===")

if __name__ == "__main__":
    analyze_ruff_errors()