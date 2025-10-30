import os
import ast
from pathlib import Path

src_dir = Path('src')
py_files = list(src_dir.rglob('*.py'))

total_files = len(py_files)
syntax_errors = 0
lines_count = 0

for py_file in py_files:
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        lines_count += len(content.splitlines())
    except SyntaxError:
        syntax_errors += 1
    except Exception:
        syntax_errors += 1

print(f'📊 代码质量统计:')
print(f'   总Python文件数: {total_files}')
print(f'   语法错误文件数: {syntax_errors}')
print(f'   总代码行数: {lines_count:,}')
print(f'   语法正确率: {((total_files-syntax_errors)/total_files*100):.1f}%')

if syntax_errors == 0:
    print('🎉 所有文件语法检查通过！')
else:
    print(f'⚠️  发现{syntax_errors}个语法错误')