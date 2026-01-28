"""
开发服务器启动脚本
"""

import os
import sys
from pathlib import Path

# Windows控制台UTF-8编码修复
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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

    # 检查 DATABASE_URL（SQLite 已移除）
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("🚨 错误: DATABASE_URL 未设置")
        print("本项目已移除 SQLite，本地开发必须使用 PostgreSQL")
        print("请在 backend/.env 中设置，例如:")
        print("  DATABASE_URL=postgresql://user:password@localhost:5432/zcgl")
        sys.exit(1)

    if database_url.startswith("sqlite://"):
        print("🚨 错误: SQLite 已移除，本项目仅支持 PostgreSQL。")
        sys.exit(1)

    # 检查 DATA_ENCRYPTION_KEY（用于PII数据加密）
    data_encryption_key = os.getenv("DATA_ENCRYPTION_KEY", "")
    if not data_encryption_key:
        print("⚠️  警告: DATA_ENCRYPTION_KEY 环境变量未设置")
        print("注意: 如果不设置此密钥，敏感数据（如个人信息）将不会被加密存储！")
        print("建议在 .env 文件中设置此密钥以保护敏感数据")
        print()
        print("生成方法:")
        print('  python -c "import secrets; print(secrets.token_urlsafe(32))"')
        print()
        print("然后将生成的密钥添加到 .env 文件:")
        print("  DATA_ENCRYPTION_KEY=<生成的密钥>")
        print()
        print("按 Enter 继续启动服务，或按 Ctrl+C 退出并配置密钥...")
        try:
            input()  # 等待用户确认
        except KeyboardInterrupt:
            print("\n取消启动")
            sys.exit(1)

    print("启动开发服务器 (DEV_MODE=true)")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT") or os.getenv("PORT", "8002"))
    uvicorn.run(
        "src.main:app", host=host, port=port, reload=True, log_level="info"
    )
