import subprocess
import sys

def check_e712_errors():
    try:
        # 运行ruff检查E712错误
        result = subprocess.run(
            ['uv', 'run', 'ruff', 'check', 'src/', '--select=E712'],
            capture_output=True,
            text=True,
            cwd='D:/code/zcgl/backend'
        )
        
        print(f"返回码: {result.returncode}")
        print(f"STDOUT 长度: {len(result.stdout)}")
        print(f"STDERR 长度: {len(result.stderr)}")
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            e712_lines = [line for line in lines if 'E712' in line and 'Avoid equality comparisons' in line]
            print(f"E712错误数量: {len(e712_lines)}")
            
            if e712_lines:
                print("\n前10个E712错误:")
                for i, line in enumerate(e712_lines[:10], 1):
                    print(f"{i}. {line}")
        else:
            print("没有找到E712错误!")
            
        if result.stderr:
            print(f"\nSTDERR: {result.stderr[:500]}")
            
    except Exception as e:
        print(f"运行检查时出错: {e}")

if __name__ == "__main__":
    check_e712_errors()