#!/usr/bin/env python3
"""Find large zero-coverage files"""
import json

with open('coverage.json') as f:
    data = json.load(f)

files = [(k, v['summary']['num_statements'], v['summary']['percent_covered'])
         for k, v in data['files'].items()]

# Find large files with 0% coverage (40+ statements)
large_uncovered = sorted([f for f in files if f[2] == 0 and f[1] > 40],
                         key=lambda x: x[1], reverse=True)

print('Large zero-coverage files (40+ statements):')
print('-' * 80)
for path, stmts, _ in large_uncovered[:20]:
    # Extract just filename from path
    fname = path.split('\\')[-1] if '\\' in path else path.split('/')[-1]
    print(f'{fname:50} {stmts:4} stmts')
