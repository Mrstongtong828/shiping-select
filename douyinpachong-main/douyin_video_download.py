# -*- coding: utf-8 -*-
"""
抖音单视频网页 - 数据包监听与无水印下载脚本
运行：py -3.11 douyin_video_download.py
"""

import json
import re
import time
import requests
from DrissionPage import Chromium, ChromiumOptions

# ======================== 配置区 ========================
VIDEO_URL = "https://www.douyin.com/video/7629300326499093779"
CHROME_PATH = ""

# requests 下载时的请求头（防 403 防盗链）
DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
}


# ======================== 工具函数 ========================
def clean_filename(name: str) -> str:
    """清洗标题，过滤掉文件名不允许的特殊字符"""
    if not name:
        return "douyin_video"
    # 保留中英文、数字、空格、常用标点，其余替换为下划线
    cleaned = re.sub(r'[\\/:*?"<>|\n\r\t]', '_', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # 截断过长的文件名
    return cleaned[:80] if cleaned else "douyin_video"


def extract_video_info(packet) -> dict:
    """
    从数据包中提取视频信息
    返回: {"title": str, "play_url": str, "duration": int}
    """
    body = packet.response.body
    result = {"title": "", "play_url": "", "duration": 0}

    try:
        # 路径 1: body.aweme_detail（标准结构）
        aweme = body.get("aweme_detail", {}) if isinstance(body, dict) else {}

        # 路径 2: body.data.aweme_detail（嵌套结构）
        if not aweme and isinstance(body, dict):
            data = body.get("data", {})
            if isinstance(data, dict):
                aweme = data.get("aweme_detail", {})

        if not aweme:
            return result

        # 提取标题
        result["title"] = aweme.get("desc", "")

        # 提取无水印播放地址
        video_info = aweme.get("video", {})
        if isinstance(video_info, dict):
            play_addr = video_info.get("play_addr", {})
            if isinstance(play_addr, dict):
                url_list = play_addr.get("url_list", [])
                if url_list:
                    result["play_url"] = url_list[0]

            # 提取时长（毫秒）
            result["duration"] = video_info.get("duration", 0)

    except Exception as e:
        print(f"  [解析异常] {e}")

    return result


def download_video(url: str, filepath: str) -> bool:
    """下载视频到本地"""
    try:
        print(f"  正在下载: {filepath}")
        resp = requests.get(url, headers=DOWNLOAD_HEADERS, stream=True, timeout=60)
        resp.raise_for_status()

        total = 0
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                total += len(chunk)

        size_mb = total / (1024 * 1024)
        print(f"  下载完成: {size_mb:.2f} MB")
        return True

    except Exception as e:
        print(f"  [下载失败] {e}")
        return False


# ======================== 主流程 ========================
def main():
    print("\n" + "=" * 55)
    print("   抖音单视频 - 无水印下载脚本")
    print("=" * 55)
    print(f"  目标链接: {VIDEO_URL}")

    # ---- 1. 启动 Chrome ----
    print("\n[1/5] 启动 Chrome...")
    co = ChromiumOptions()
    if CHROME_PATH:
        co.set_browser_path(CHROME_PATH)
    browser = Chromium(co)
    tab = browser.latest_tab

    # ---- 2. 访问抖音首页（确保登录态） ----
    print("[2/5] 访问抖音首页，等待 60 秒供扫码登录...")
    tab.get("https://www.douyin.com")
    time.sleep(60)

    # ---- 3. 开启监听（必须在访问视频页之前） ----
    print("[3/5] 开启 aweme/detail 监听...")
    tab.listen.start("aweme/detail")

    # ---- 4. 访问视频页，等待数据包 ----
    print(f"[4/5] 访问视频页: {VIDEO_URL}")
    tab.get(VIDEO_URL)
    time.sleep(3)  # 等待页面渲染

    # 模拟轻微滚动触发加载
    tab.scroll.down(300)
    time.sleep(2)

    print("  等待数据包返回...")
    packet = tab.listen.wait(timeout=20)

    if not packet:
        print("\n[失败] 未捕获到 aweme/detail 数据包")
        return

    print(f"  捕获成功: {packet.url[:80]}...")

    # ---- 5. 解析并下载 ----
    print("[5/5] 解析视频信息并下载...")
    info = extract_video_info(packet)

    if not info["play_url"]:
        print("\n[失败] 未提取到播放地址，保存原始数据供分析...")
        with open("douyin_raw_debug.json", "w", encoding="utf-8") as f:
            json.dump(packet.response.body, f, ensure_ascii=False, indent=2)
        print("  原始数据已保存: douyin_raw_debug.json")
        return

    filename = clean_filename(info["title"]) + ".mp4"
    print(f"  视频标题: {info['title'][:50]}...")
    print(f"  文件名: {filename}")
    print(f"  时长: {info['duration'] / 1000:.1f} 秒")

    success = download_video(info["play_url"], filename)

    if success:
        print(f"\n  视频已保存至: {filename}")
    else:
        print("\n  下载失败，将播放地址写入文件供手动下载...")
        with open("douyin_play_url.txt", "w", encoding="utf-8") as f:
            f.write(info["play_url"])
        print("  播放地址已保存: douyin_play_url.txt")


if __name__ == "__main__":
    main()
