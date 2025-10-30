# 查找contract_template_learner.py中所有未闭合的try块
with open('src/services/contract_template_learner.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 检查第337行附近的详细内容
for i in range(330, 345):
    if i < len(lines):
        print(f'{i+1}: {repr(lines[i])}')