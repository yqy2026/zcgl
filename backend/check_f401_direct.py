import os
import subprocess

# 切换到backend目录
os.chdir('D:\\code\\zcgl\\backend')

# 运行ruff检查F401错误
result = subprocess.run(['uv', 'run', 'ruff', 'check', 'src/', '--select=F401'], 
                       capture_output=True, text=True)

print("F401错误检查结果:")
print("=" * 60)
print(result.stdout)

if result.stderr:
    print("错误信息:")
    print(result.stderr)

print(f"返回码: {result.returncode}")