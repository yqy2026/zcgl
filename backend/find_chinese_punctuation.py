# 查找performance_service.py中的所有中文标点符号
with open('src/services/performance_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

chinese_punctuation = []
for i, line in enumerate(lines):
    # 查找中文标点符号
    for char in line:
        if ord(char) > 0x4e00 and ord(char) < 0x9fff:  # 中文字符范围
            continue
        elif ord(char) > 0xff00 and ord(char) < 0xffff:  # 全角字符范围
            if char not in ['\n', '\r', '\t', ' ', '"', "'", ':', ',', '.', '(', ')', '[', ']', '{', '}', '-', '_', '=', '+', '/', '*', '%', '<', '>', '!', '?', ';']:
                chinese_punctuation.append((i+1, char, line.strip()))

if chinese_punctuation:
    print("Found Chinese punctuation:")
    for line_num, char, context in chinese_punctuation:
        print(f"Line {line_num}: '{char}' in: {context}")
else:
    print("No Chinese punctuation found")