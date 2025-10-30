# 读取并显示文件内容
with open('src/services/contract_template_learner.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 显示330-345行的内容
for i in range(330, 345):
    if i < len(lines):
        print(f'{i+1}: {repr(lines[i])}')