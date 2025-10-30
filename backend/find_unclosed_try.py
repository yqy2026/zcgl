# 查找contract_template_learner.py中所有未闭合的try块
with open('src/services/contract_template_learner.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

current_try_start = None
try_blocks = []

for i, line in enumerate(lines):
    stripped = line.strip()
    
    if stripped == 'try:':
        current_try_start = i + 1
    elif current_try_start and (stripped.startswith('except') or stripped.startswith('finally')):
        current_try_start = None
    elif current_try_start and stripped.startswith('def ') and i > 0:
        # 在try块中遇到新的函数定义
        try_blocks.append((current_try_start, i + 1))
        current_try_start = None

if current_try_start:
    try_blocks.append((current_try_start, len(lines)))

print("Found unclosed try blocks:")
for start, end in try_blocks:
    print(f"Lines {start}-{end}")
    # 显示上下文
    context_start = max(0, start - 3)
    context_end = min(len(lines), end + 3)
    for i in range(context_start, context_end):
        marker = ">>> " if i == start - 1 else "    "
        print(f"{marker}{i + 1}: {repr(lines[i])}")
    print()