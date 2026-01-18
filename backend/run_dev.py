"""
开发服务器启动脚本
"""

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置开发模式环境变量
os.environ.setdefault("DEV_MODE", "true")

if __name__ == "__main__":
    # 在启动前验证环境配置
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  警告: 未找到 .env 文件")
        print("请从 .env.example 复制并配置环境变量")
        print("运行: cp .env.example .env")
        print("然后编辑 .env 文件，至少设置 SECRET_KEY（32+字符）")
        sys.exit(1)

    # 检查 SECRET_KEY（虽然 config.py 会强制要求，但这里提供更友好的提示）
    secret_key = os.getenv("SECRET_KEY", "")
    if not secret_key or len(secret_key) < 32:
        print("🚨 错误: SECRET_KEY 环境变量未正确设置")
        print("请在 .env 文件中设置强随机密钥（32+字符）")
        print()
        print("生成方法:")
        print('  python -c "import secrets; print(secrets.token_urlsafe(32))"')
        print()
        print("然后将生成的密钥添加到 .env 文件:")
        print("  SECRET_KEY=<生成的密钥>")
        sys.exit(1)

    print("启动开发服务器 (DEV_MODE=true)")
    uvicorn.run(
        "src.main:app", host="0.0.0.0", port=8002, reload=True, log_level="info"
    )
