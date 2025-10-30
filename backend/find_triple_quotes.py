# 查找excel_export.py中的三引号问题
with open('src/services/excel_export.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找所有三引号
import re
triple_quotes = re.finditer(r'""".*?"""', content, re.DOTALL)
positions = []
for match in triple_quotes:
    positions.append((match.start(), match.end(), match.group()[:50]))

print(f"Found {len(positions)} triple-quoted strings")
for start, end, preview in positions:
    line_num = content[:start].count('\n') + 1
    print(f"Line {line_num}: {preview}...")

# 检查是否有未闭合的三引号
lines = content.split('\n')
for i, line in enumerate(lines):
    if '"""' in line:
        quotes = line.count('"""')
        if quotes % 2 == 1:  # 奇数个三引号
            print(f"Line {i+1} may have unclosed triple quote: {repr(line)}")