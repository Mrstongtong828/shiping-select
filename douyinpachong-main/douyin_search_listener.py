# -*- coding: utf-8 -*-
"""
抖音搜索页数据包监听脚本 (防 403 版)
安装：py -3.11 -m pip install DrissionPage
运行：py -3.11 douyin_search_listener.py
"""

import json
import os
import re
import random
import time
import sys
from datetime import datetime
from DrissionPage import Chromium, ChromiumOptions

KEYWORD = "佛山中考数学"
SEARCH_URL = f"https://www.douyin.com/search/{KEYWORD}?type=video"
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foshan_hot_videos.json")
CHROME_PATH = ""
MAX_VIDEOS = 5


def clean_title(title: str) -> str:
    if not title:
        return "无标题"
    return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？、；：""''（）《》_,.!?;:() -]', '', title).strip() or "无标题"


def extract_videos(packet) -> tuple:
    body = packet.response.body
    raw_json = body if isinstance(body, dict) else {}
    data_list = None
    if isinstance(body, dict):
        if isinstance(body.get('data'), list):
            data_list = body['data']
        elif isinstance(body.get('data'), dict):
            inner = body['data']
            if isinstance(inner.get('data'), list):
                data_list = inner['data']
            elif isinstance(inner.get('aweme_list'), list):
                data_list = inner['aweme_list']
        if not data_list and isinstance(body.get('aweme_list'), list):
            data_list = body['aweme_list']
    elif isinstance(body, list):
        data_list = body
    if not data_list:
        return [], raw_json
    videos = []
    for i, item in enumerate(data_list):
        if i >= MAX_VIDEOS:
            break
        if not isinstance(item, dict):
            continue
        aweme = item.get('aweme_info', item)
        aweme_id = aweme.get('aweme_id', '')
        title = clean_title(aweme.get('desc', ''))
        digg_count = 0
        statistics = aweme.get('statistics', {})
        if isinstance(statistics, dict):
            digg_count = statistics.get('digg_count') or statistics.get('heart_count') or statistics.get('like_count') or 0
        # 提取底层 CDN 流链接：play_addr -> url_list
        play_url = ""
        play_addr = aweme.get('video', {}).get('play_addr', {})
        url_list = play_addr.get('url_list', []) if isinstance(play_addr, dict) else []
        for url in url_list:
            if isinstance(url, str) and 'v11' in url:
                play_url = url
                break
        if not play_url and url_list:
            play_url = url_list[0]

        if aweme_id:
            videos.append({
                "序号": i + 1,
                "标题": title,
                "官网链接": f"https://www.douyin.com/video/{aweme_id}",
                "底层流链接": play_url,
                "点赞数": digg_count,
            })
    return videos, raw_json


def main():
    print("\n" + "=" * 55)
    print("   抖音搜索页数据包监听脚本（防 403 官网链接版）")
    print("=" * 55)

    co = ChromiumOptions()
    if CHROME_PATH:
        co.set_browser_path(CHROME_PATH)
    print("\n[1/6] 正在启动 Chrome...")
    browser = Chromium(co)
    tab = browser.latest_tab

    try:
        tab.get("https://www.douyin.com")
        print("\n" + "!" * 50)
        print("  请在浏览器中扫码登录！等待 90 秒后自动继续")
        print("!" * 50)
        time.sleep(90)

        print("\n[2/6] 开启搜索接口监听...")
        tab.listen.start(targets=['search', 'aweme/v1'], res_type='xhr')

        print(f"[3/6] 访问搜索页: {SEARCH_URL}")
        tab.get(SEARCH_URL)
        time.sleep(3)

        print("[4/6] 模拟人类缓慢滚动...")
        for loop in range(random.randint(2, 3)):
            px = random.randint(300, 600)
            tab.scroll.down(px)
            slp = random.uniform(4.0, 7.5)
            print(f"      滚动 {px}px，休眠 {slp:.1f}s")
            time.sleep(slp)

        print("[5/6] 等待数据包...")
        packet = None
        for p in tab.listen.steps(timeout=20):
            url = p.url
            print(f"      捕获: {url[:80]}...")
            if 'search' in url and 'aweme' in url:
                packet = p
                break
        if not packet:
            print("[失败] 未捕获到搜索数据包")
            browser.quit()
            sys.exit(1)
        print(f"[成功] {packet.url}")

        print("[6/6] 解析数据...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            videos, raw_json = extract_videos(packet)
            if videos:
                result = {"搜索关键词": KEYWORD, "采集时间": timestamp, "视频数量": len(videos),
                          "说明": "链接为官网网页端地址，可直接浏览器打开", "视频列表": videos}
                print(f"\n  提取到 {len(videos)} 条视频：")
                for v in videos:
                    print(f"    [{v['序号']}] {v['标题'][:35]}... 点赞:{v['点赞数']}")
                    print(f"         官网: {v['官网链接']}")
                    print(f"         流: {v['底层流链接'][:80]}..." if v['底层流链接'] else "         流: (未获取到)")
            else:
                result = {"搜索关键词": KEYWORD, "采集时间": timestamp, "状态": "解析失败", "原始数据": raw_json}
                print("\n  未找到 aweme_id，已保存原始 JSON")
        except Exception as e:
            result = {"搜索关键词": KEYWORD, "采集时间": timestamp, "状态": f"异常: {e}", "原始数据": str(packet.response.body)}
            print(f"\n  解析异常: {e}")

        with open(SAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n  已保存: {SAVE_PATH}")

    finally:
        print("\n[退出] 正在关闭浏览器...")
        browser.quit()
        print("[退出] 进程结束")
        sys.exit(0)


if __name__ == '__main__':
    main()
