# 查找try语句
with open('src/services/contract_template_learner.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_try = False
try_lines = []

for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == 'try:':
        in_try = True
        try_lines.append(i + 1)
    elif in_try and (stripped.startswith('except') or stripped.startswith('finally')):
        in_try = False
    elif in_try and stripped.startswith('def ') and i > 0:
        # 如果在try块中遇到新的函数定义，可能是问题
        print(f"Possible missing except/finally before line {i + 1}: {stripped}")

print(f"Found try statements at lines: {try_lines}")

# 检查最后几个try语句的状态
for line_num in try_lines[-3:]:  # 检查最后3个try
    print(f"\nAround line {line_num}:")
    start = max(0, line_num - 5)
    end = min(len(lines), line_num + 10)
    for i in range(start, end):
        marker = ">>> " if i == line_num - 1 else "    "
        print(f"{marker}{i + 1}: {repr(lines[i])}")