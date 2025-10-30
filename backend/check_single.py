import sys

file_path = 'src/services/contract_template_learner.py'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    compile(content, file_path, 'exec')
    print('Syntax OK')
except SyntaxError as e:
    print(f'Syntax error: {e}')
    print(f'Line {e.lineno}: {e.text}')
except Exception as e:
    print(f'Error: {e}')