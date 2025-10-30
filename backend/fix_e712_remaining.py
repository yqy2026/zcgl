import json
import re

# 读取ruff错误报告
with open('ruff_errors.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 筛选E712错误
e712_errors = [error for error in data if error.get('code') == 'E712']

# 按文件分组
files_with_errors = {}
for error in e712_errors:
    filename = error['filename']
    if filename not in files_with_errors:
        files_with_errors[filename] = []
    files_with_errors[filename].append(error)

print(f"需要修复的文件数量: {len(files_with_errors)}")

# 定义修复模式
patterns = [
    (r'(\w+)\.is_deleted == False', r'not \1.is_deleted'),
    (r'(\w+)\.is_active == True', r'\1.is_active'),
    (r'(\w+)\.is_deleted == True', r'\1.is_deleted'),  # 这种情况较少
    (r'(\w+)\.is_active == False', r'not \1.is_active'),  # 这种情况较少
]

def fix_file_e712_errors(filename, errors):
    """修复单个文件中的E712错误"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_applied = []
        
        for error in errors:
            line_num = error['location']['row'] - 1  # 转换为0-based索引
            message = error['message']
            
            # 根据消息类型确定修复方式
            if 'is_deleted == False' in message:
                # 查找模式: EnumFieldType.is_deleted == False
                old_pattern = r'(\w+)\.is_deleted == False'
                new_pattern = r'not \1.is_deleted'
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    fixes_applied.append(f"行 {error['location']['row']}: is_deleted == False → not is_deleted")
            
            elif 'is_active == True' in message:
                # 查找模式: EnumFieldUsage.is_active == True
                old_pattern = r'(\w+)\.is_active == True'
                new_pattern = r'\1.is_active'
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    fixes_applied.append(f"行 {error['location']['row']}: is_active == True → is_active")
            
            elif 'is_deleted == True' in message:
                # 查找模式: SomeModel.is_deleted == True
                old_pattern = r'(\w+)\.is_deleted == True'
                new_pattern = r'\1.is_deleted'
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    fixes_applied.append(f"行 {error['location']['row']}: is_deleted == True → is_deleted")
            
            elif 'is_active == False' in message:
                # 查找模式: SomeModel.is_active == False
                old_pattern = r'(\w+)\.is_active == False'
                new_pattern = r'not \1.is_active'
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    fixes_applied.append(f"行 {error['location']['row']}: is_active == False → not is_active")
        
        if content != original_content:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fixes_applied
        else:
            return False, []
            
    except Exception as e:
        print(f"修复文件 {filename} 时出错: {e}")
        return False, []

# 批量修复文件
fixed_files = 0
total_fixes = 0

for filename, errors in files_with_errors.items():
    print(f"\n修复文件: {filename}")
    print(f"错误数量: {len(errors)}")
    
    fixed, fixes = fix_file_e712_errors(filename, errors)
    if fixed:
        fixed_files += 1
        total_fixes += len(fixes)
        print("应用的修复:")
        for fix in fixes:
            print(f"  - {fix}")
    else:
        print("  未应用修复")

print(f"\n修复完成!")
print(f"修复的文件数量: {fixed_files}")
print(f"应用的总修复数量: {total_fixes}")