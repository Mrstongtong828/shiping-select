"""
飞书 Webhook 推送脚本 - 佛山本地教育热点视频卡片
用法: python feishu_webhook_push.py

Webhook 地址获取方式:
  1. 打开飞书群 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人
  2. 复制生成的 Webhook 地址填入下方 WEBHOOK_URL
"""

import json
import os
import requests

# ============================================================
# 【必填】飞书机器人 Webhook 地址
# 获取方式: 飞书群 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人 → 复制 Webhook
# ============================================================
WEBHOOK_URL = "在此填入飞书机器人Webhook地址"

# 数据文件路径
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foshan_hot_videos.json")


def load_videos(path: str, top_n: int = 3) -> tuple:
    """读取 JSON 并返回前 top_n 条视频及元信息"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    keyword = data.get("搜索关键词", "")
    collect_time = data.get("采集时间", "")
    videos = data.get("视频列表", [])[:top_n]
    return keyword, collect_time, videos


def build_card(keyword: str, collect_time: str, videos: list) -> dict:
    """组装飞书消息卡片 payload"""

    # ---- 构建 Markdown 内容行 ----
    md_lines = []
    for v in videos:
        seq = v.get("序号", "")
        title = v.get("标题", "无标题")
        url = v.get("官网链接", "")
        likes = v.get("点赞数", 0)

        md_lines.append(f"**{seq}. {title}**")
        md_lines.append(f"👍 点赞数：**{likes}**")
        # 底层保留真实 URL，前端展示中文标签，辅助机器人可从报文提取原始链接
        md_lines.append(f"🔗 [无水印播放地址]({url})")
        md_lines.append("")  # 空行分隔

    markdown_content = "\n".join(md_lines)

    # ---- 组装卡片 JSON ----
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🔥 佛山本地教育热点推送"
                },
                "template": "red"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"**搜索关键词**：{keyword}\n**采集时间**：{collect_time}\n**推送数量**：TOP {len(videos)}"
                },
                {"tag": "hr"},
                {
                    "tag": "markdown",
                    "content": markdown_content
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "由市场部自动化脚本推送 | 请总监审核后回复"
                        }
                    ]
                }
            ]
        }
    }
    return card


def push_to_feishu(payload: dict) -> None:
    """发送卡片到飞书 Webhook"""
    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        resp = requests.post(WEBHOOK_URL, headers=headers, json=payload, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            print("[成功] 卡片消息已推送到飞书群！")
        else:
            print(f"[失败] 飞书返回错误: {result}")
    except requests.exceptions.RequestException as e:
        print(f"[异常] 网络请求失败: {e}")


def main():
    keyword, collect_time, videos = load_videos(DATA_FILE, top_n=3)
    if not videos:
        print("[警告] 未读取到视频数据，请检查 JSON 文件。")
        return
    card_payload = build_card(keyword, collect_time, videos)
    push_to_feishu(card_payload)


if __name__ == "__main__":
    main()
