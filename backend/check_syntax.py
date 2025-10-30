import sys

# 检查语法错误的文件
files_to_check = [
    'src/services/backup_service.py',
    'src/services/contract_template_learner.py', 
    'src/services/excel_export.py',
    'src/services/history_tracker.py',
    'src/services/performance_service.py'
]

for file_path in files_to_check:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        compile(content, file_path, 'exec')
        print(f'{file_path}: Syntax OK')
    except SyntaxError as e:
        print(f'{file_path}: Syntax error at line {e.lineno}: {e}')
        if e.text:
            print(f'  Line {e.lineno}: {e.text.strip()}')
    except Exception as e:
        print(f'{file_path}: Error: {e}')