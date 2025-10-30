import json
from collections import defaultdict

# 读取ruff错误报告
with open('ruff_errors.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 筛选E712错误
e712_errors = [error for error in data if error.get('code') == 'E712']

# 按文件分组
files_with_errors = defaultdict(list)
for error in e712_errors:
    files_with_errors[error['filename']].append(error)

print("E712布尔值比较错误分析报告")
print("=" * 50)
print(f"总共发现 {len(e712_errors)} 个E712错误")
print(f"涉及 {len(files_with_errors)} 个文件")
print()

# 按文件分析
for filename, errors in sorted(files_with_errors.items()):
    print(f"\n文件: {filename}")
    print(f"错误数量: {len(errors)}")
    print("错误详情:")
    
    for i, error in enumerate(errors, 1):
        location = error['location']
        message = error['message']
        print(f"  {i}. 行 {location['row']}, 列 {location['column']}: {message}")
        
        # 分析错误类型
        if '== True' in message:
            error_type = "== True (应移除比较)"
        elif '== False' in message:
            error_type = "== False (应改为 not)"
        elif '!= True' in message:
            error_type = "!= True (应改为 not)"
        elif '!= False' in message:
            error_type = "!= False (应移除比较)"
        else:
            error_type = "其他布尔值比较"
            
        print(f"     类型: {error_type}")
        
        if 'fix' in error and error['fix']:
            print(f"     建议: {error['fix']['message']}")
    print("-" * 40)

print("\n修复建议:")
print("1. == True  → 直接移除 == True")
print("2. == False → 改为 not 运算符")  
print("3. != True  → 改为 not 运算符")
print("4. != False → 直接移除 != False")