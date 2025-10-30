import json

# 读取ruff错误文件
with open('ruff_errors.json', 'r', encoding='utf-8') as f:
    errors = json.load(f)

# 筛选F401错误
f401_errors = [err for err in errors if err['code'] == 'F401']

print(f"找到 {len(f401_errors)} 个F401未使用导入错误:")
print("=" * 80)

# 按文件分组
files_with_f401 = {}
for err in f401_errors:
    filename = err['filename']
    if filename not in files_with_f401:
        files_with_f401[filename] = []
    files_with_f401[filename].append(err)

# 显示每个文件的F401错误
for filename, errors in files_with_f401.items():
    print(f"\n文件: {filename}")
    print("-" * 60)
    for err in errors:
        row = err['location']['row']
        message = err['message']
        print(f"  行 {row}: {message}")