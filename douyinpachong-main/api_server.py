# -*- coding: utf-8 -*-
"""
FastAPI 服务 - 将抖音爬虫脚本封装为 Web 接口供 Coze 调用
启动：py -3.11 api_server.py
接口：GET http://127.0.0.1:8000/api/get_hot_videos
"""

import subprocess
import json
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

# 使用绝对路径，不受终端工作目录影响
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "douyin_search_listener.py")
JSON_PATH = os.path.join(BASE_DIR, "foshan_hot_videos.json")


@app.get("/api/get_hot_videos")
async def get_hot_videos():
    try:
        if not os.path.exists(SCRIPT_PATH):
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"脚本文件不存在: {SCRIPT_PATH}"}
            )

        result = subprocess.run(
            ["py", "-3.11", SCRIPT_PATH],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"脚本执行失败: {result.stderr}"}
            )

        if not os.path.exists(JSON_PATH):
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"结果文件不存在: {JSON_PATH}"}
            )

        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {"status": "success", "data": data}

    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "脚本执行超时（120秒）"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"未知错误: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
