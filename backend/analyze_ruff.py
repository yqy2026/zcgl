# 读取ruff检查结果并分析
import subprocess
import json

result = subprocess.run(['.venv\\Scripts\\ruff', 'check', 'src\\', '--output-format=json'], 
                       capture_output=True, text=True, cwd='D:\\code\\zcgl\\backend')

try:
    data = json.loads(result.stdout)
    from collections import defaultdict
    error_counts = defaultdict(int)
    
    for item in data:
        error_counts[item['code']] += 1
    
    print('剩余问题分布:')
    total = 0
    for code, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f'{code}: {count}')
        total += count
    
    print(f'\n总计: {len(data)} 个问题')
    print(f'主要问题类型: {len(error_counts)} 种')
    
except json.JSONDecodeError:
    print("Failed to parse JSON output")
    print("Raw output length:", len(result.stdout))