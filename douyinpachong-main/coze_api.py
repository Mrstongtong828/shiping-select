# -*- coding: utf-8 -*-
"""
Coze 工作流对接脚本
读取本地热点视频 JSON，将数据发送至 Coze 云端生成剧本
"""

import json
import requests
import sys
import os

# ============================================================
# 【必填】全局配置 - 请在运行前填入你自己的真实信息
# ============================================================
COZE_API_TOKEN = "your_coze_api_token"
WORKFLOW_ID = "your_coze_workflow_id"

# 数据文件路径
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foshan_hot_videos.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coze_generated_script.json")

# API 端点
API_URL = "https://api.coze.cn/v1/workflow/run"


def load_top_video(path: str) -> dict:
    """从 JSON 文件中读取热度最高的第 1 条视频"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    videos = data.get("视频列表", [])
    if not videos:
        print("‼️  错误：JSON 文件中没有视频数据！")
        sys.exit(1)

    top = videos[0]
    title = top.get("标题", "")
    # 优先取底层流链接（v11），无则用官网链接
    play_url = top.get("底层流链接", "")
    if not play_url:
        play_url = top.get("官网链接", "")

    if not title or not play_url:
        print("‼️  错误：第一条视频数据不完整，缺少标题或链接！")
        sys.exit(1)

    return {"title": title, "url": play_url}


def build_payload(title: str, url: str) -> dict:
    """组装 Coze 工作流请求体"""
    return {
        "workflow_id": WORKFLOW_ID,
        "parameters": {
            "input": f"参考热点视频标题：{title}\n视频源链接：{url}",
            "compete_name": "",
            "task_type": "短视频脚本"
        }
    }


def call_coze(payload: dict) -> str:
    """调用 Coze 工作流 API，返回生成的剧本文本"""
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    print("🚀 正在将数据发射至 Coze 云端大脑...")
    print("🧠 大模型正在拼命写剧本中 (约需30-60秒)...")

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)

    if resp.status_code != 200:
        print(f"‼️  请求失败！状态码：{resp.status_code}")
        print(f"‼️  响应内容：{resp.text}")
        sys.exit(1)

    result = resp.json()

    # Coze 正常返回 code=0
    if result.get("code") != 0:
        print(f"‼️  Coze 返回错误：{result.get('msg', '未知错误')}")
        print(f"‼️  完整响应：{json.dumps(result, ensure_ascii=False, indent=2)}")
        sys.exit(1)

    # 提取 data 字段中的剧本内容
    # Coze 返回的 data 是 JSON 字符串，需二次解析
    raw_data = result.get("data", "")
    if isinstance(raw_data, str):
        try:
            data_dict = json.loads(raw_data)
        except json.JSONDecodeError:
            data_dict = {}
    elif isinstance(raw_data, dict):
        data_dict = raw_data
    else:
        data_dict = {}

    # 遍历 output / output1 / output2 / ... 取第一个非空值
    script_text = ""
    for key in sorted(data_dict.keys()):
        val = data_dict.get(key, "")
        if val and isinstance(val, str) and len(val) > 10:
            script_text = val
            break

    if not script_text:
        print("‼️  Coze 返回的剧本内容为空，请检查工作流配置。")
        print(f"‼️  完整响应：{json.dumps(result, ensure_ascii=False, indent=2)}")
        sys.exit(1)

    return script_text


def save_result(title: str, script_text: str, path: str):
    """将结果保存为 JSON 文件"""
    output = {
        "原标题": title,
        "Coze生成的剧本": script_text
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    # 前置检查配置
    if "在此填入" in COZE_API_TOKEN or "在此填入" in WORKFLOW_ID:
        print("‼️  请先在 coze_api.py 顶部填入 COZE_API_TOKEN 和 WORKFLOW_ID！")
        sys.exit(1)

    print("=" * 50)
    print("🤖 Coze 工作流剧本生成器")
    print("=" * 50)

    # 第一步：读取数据
    print()
    print("📂 正在读取热点视频数据...")
    video = load_top_video(DATA_FILE)
    print(f"   标题：{video['title']}")
    print(f"   链接：{video['url'][:80]}...")

    # 第二步：组装请求
    print()
    payload = build_payload(video["title"], video["url"])

    # 第三步：调用 Coze API
    print()
    try:
        script_text = call_coze(payload)
    except requests.exceptions.Timeout:
        print("‼️  请求超时（120秒），Coze 服务响应过慢，请稍后重试。")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"‼️  网络请求异常：{e}")
        sys.exit(1)

    # 第四步：保存结果
    print()
    print("✅ 剧本生成成功！")
    save_result(video["title"], script_text, OUTPUT_FILE)
    print(f"💾 已保存至：{OUTPUT_FILE}")

    print()
    print("=" * 50)
    print("🎉 Coze 剧本生成流程完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
