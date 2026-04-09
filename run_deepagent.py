#!/usr/bin/env python3
"""deepagent 开发服务器启动脚本"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src_deepagent.main:app",
        host="0.0.0.0",
        port=9001,
        reload=True,
        reload_dirs=["src_deepagent"],
    )
