"""
开发服务器启动脚本
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8002,
        reload=True,
        log_level="info"
    )