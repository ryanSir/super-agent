#!/usr/bin/env python3
"""开发服务器启动脚本"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        reload_dirs=["src"],  # 只监听 src/ 目录
    )
