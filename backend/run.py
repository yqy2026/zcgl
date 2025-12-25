#!/usr/bin/env python3
"""
应用启动脚本
"""

import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    import uvicorn

    from src.main import app

    print("启动土地物业资产管理系统 - 完整版API")
    print("访问地址:")
    print("   API: http://localhost:8002")
    print("   文档: http://localhost:8002/docs")
    print("   健康检查: http://localhost:8002/health")
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
        reload=False,
        log_level="info"
    )
