# 修复performance_service.py中的编码问题
with open('src/services/performance_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换已知的编码问题
replacements = [
    ('优化的计数查�?', '优化的计数查询'),
    ('应用优化的排序（利用索引�?', '应用优化的排序(利用索引)'),
    ('应用优化的筛选条�?', '应用优化的筛选条件'),
    ('优化的统计查�?', '优化的统计查询'),
    ('优化的历史记录查�?', '优化的历史记录查询'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"Replaced: {old} -> {new}")

with open('src/services/performance_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed encoding issues in performance_service.py")