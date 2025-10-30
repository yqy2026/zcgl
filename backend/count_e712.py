import json

# 读取ruff错误报告
with open('ruff_errors.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 筛选E712错误
e712_errors = [error for error in data if error.get('code') == 'E712']

print(f"找到 {len(e712_errors)} 个E712布尔值比较错误")
print("\n前10个E712错误:")
for i, error in enumerate(e712_errors[:10], 1):
    print(f"\n{i}. 文件: {error['filename']}")
    print(f"   位置: 行 {error['location']['row']}, 列 {error['location']['column']}")
    print(f"   消息: {error['message']}")
    if 'fix' in error and error['fix']:
        print(f"   建议修复: {error['fix']['message']}")

print(f"\n总共需要修复 {len(e712_errors)} 个E712错误")