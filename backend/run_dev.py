"""
开发服务器启动脚本
"""

import os

import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置开发模式环境变量
os.environ.setdefault("DEV_MODE", "true")

if __name__ == "__main__":
    print("启动开发服务器 (DEV_MODE=true)")
    uvicorn.run(
        "src.main:app", host="0.0.0.0", port=8002, reload=True, log_level="info"
    )
