#!/usr/bin/env python3
"""
应用启动脚本
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print("🚀 启动土地物业资产管理系统 - 完整版API")
    print("📱 访问地址:")
    print("   API: http://localhost:8001")
    print("   文档: http://localhost:8001/docs")
    print("   健康检查: http://localhost:8001/health")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )