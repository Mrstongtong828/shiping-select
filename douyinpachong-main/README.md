#钟某制造的抖音爬虫工具集

## 文件说明

| 文件 | 功能 | 运行命令 |
|------|------|----------|
| `douyin_search_listener.py` | 搜索页数据包监听，提取视频列表 | `py -3.11 douyin_search_listener.py` |
| `douyin_video_download.py` | 单视频无水印下载 | `py -3.11 douyin_video_download.py` |
| `douyin_smart_download.py` | 智能登录版（自动复用 Cookie） | `py -3.11 douyin_smart_download.py` |
| `test_chrome.py` | Chrome 启动测试 | `py -3.11 test_chrome.py` |

## 数据文件

| 文件 | 说明 |
|------|------|
| `foshan_hot_videos.json` | 搜索结果（视频列表+官网链接） |
| `douyin_video_links.json` | 单视频播放地址（CDN 流链接） |

## 使用前提

1. 安装依赖：`py -3.11 -m pip install DrissionPage`
2. 系统已安装 Chrome 浏览器
3. 首次运行需扫码登录，后续会自动复用登录态

## 修改配置

每个脚本顶部有配置区，可修改：
- `VIDEO_URL` — 目标视频链接
- `KEYWORD` — 搜索关键词
- `CHROME_PATH` — Chrome 路径
