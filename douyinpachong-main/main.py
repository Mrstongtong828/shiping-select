"""
总控调度脚本：全自动无人值守流水线
执行链路：数据抓取 → 飞书推送
"""

import sys
import subprocess
import os
import shutil

# 数据文件路径
DATA_FILE = "foshan_hot_videos.json"


def get_python_exe() -> str:
    """
    获取合适的 Python 解释器路径。
    优先使用 py -3.11（DrissionPage 兼容性要求），
    若不可用则回退到当前解释器 sys.executable。
    """
    # 方式1：尝试 py launcher 调用 3.11
    try:
        r = subprocess.run(["py", "-3.11", "--version"], capture_output=True, text=True)
        if r.returncode == 0:
            # 获取 3.11 的真实路径
            r2 = subprocess.run(
                ["py", "-3.11", "-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True
            )
            if r2.returncode == 0:
                path = r2.stdout.strip()
                if os.path.isfile(path):
                    return path
    except FileNotFoundError:
        pass

    # 方式2：尝试直接调用 python3.11
    for name in ["python3.11", "python3.11.exe"]:
        path = shutil.which(name)
        if path:
            return path

    # 方式3：回退到当前解释器
    print("⚠️  未找到 Python 3.11，使用当前解释器:", sys.executable)
    return sys.executable


def main():
    python_exe = get_python_exe()
    py_version = "未知"
    try:
        r = subprocess.run([python_exe, "--version"], capture_output=True, text=True)
        if r.returncode == 0:
            py_version = r.stdout.strip()
    except Exception:
        pass

    print("=" * 50)
    print("🎬 开卓视频工厂自动化流水线已启动...")
    print(f"🐍 解释器: {python_exe}")
    print(f"🐍 版本:   {py_version}")
    print("=" * 50)

    # ───────────────────────────────────────────────
    # 第一步：数据抓取
    # ───────────────────────────────────────────────
    print()
    print("⏳ [1/2] 正在执行数据抓取任务 (douyin_search_listener.py)...")

    result = subprocess.run([python_exe, "douyin_search_listener.py"])

    # 状态拦截：检查退出码
    if result.returncode != 0:
        print()
        print("‼️  错误：数据抓取脚本异常退出！")
        print(f"‼️  退出状态码：{result.returncode}")
        print("‼️  流水线已中止，未执行飞书推送。")
        sys.exit(1)

    # 状态拦截：检查数据文件是否生成
    if not os.path.isfile(DATA_FILE):
        print()
        print(f"‼️  错误：抓取完成但未生成数据文件 [{DATA_FILE}]！")
        print("‼️  流水线已中止，未执行飞书推送。")
        sys.exit(1)

    print("✅ 抓取完成！")

    # ───────────────────────────────────────────────
    # 第二步：飞书推送
    # ───────────────────────────────────────────────
    print()
    print("⏳ [2/2] 正在推送飞书卡片 (feishu_webhook_push.py)...")

    result = subprocess.run([python_exe, "feishu_webhook_push.py"])

    if result.returncode != 0:
        print()
        print("‼️  错误：飞书推送脚本异常退出！")
        print(f"‼️  退出状态码：{result.returncode}")
        sys.exit(1)

    print("✅ 推送完成！")

    # ───────────────────────────────────────────────
    # 流水线结束
    # ───────────────────────────────────────────────
    print()
    print("=" * 50)
    print("🎉 恭喜！今日流水线任务全部圆满完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
