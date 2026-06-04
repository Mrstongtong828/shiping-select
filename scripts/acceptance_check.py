from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.env_utils import is_real_env_value  # noqa: E402

MOJIBAKE_MARKERS = (
    "涓",
    "鎶",
    "瀛",
    "鍏滃簳",
    "绉戞櫘",
    "鏈",
    "瑙嗛",
    "���",
)

REQUIRED_FILES = (
    "goal.md",
    "README.md",
    "pyproject.toml",
    "main.py",
    "app.py",
    "requirements.txt",
    ".env.example",
    "scripts/acceptance_check.py",
    "scripts/preflight_check.py",
    "scripts/refresh_submission_samples.py",
    "scripts/package_submission.py",
    "scripts/final_audit.py",
    "scripts/generate_demo_recording.py",
    "scripts/run_final_acceptance.py",
    "scripts/verify_cache.py",
    "scripts/verify_asr.py",
    "scripts/verify_streamlit_ui.py",
    "prompts/eval_template.txt",
    "src/schema.py",
    "src/exporters.py",
    "src/cache_utils.py",
    "src/env_utils.py",
    "src/asr_whisper.py",
    "src/search_bilibili.py",
    "src/search_youtube.py",
    "src/search_douyin.py",
    "文档/验收状态表.md",
    "文档/README.md",
    "文档/Prompt迭代记录.md",
    "文档/反思报告.md",
    "文档/抖音抓取降级说明与工程代价对比.md",
    "文档/终验运行记录.md",
    "文档/周报/Week01_周报.md",
    "文档/周报/Week02_周报.md",
    "文档/周报/Week03_周报.md",
    "文档/周报/Week04_周报.md",
    "评估表/人工对照评估表.csv",
    "评估表/人工对照评估结果.md",
    "答辩/答辩大纲.md",
    "答辩/答辩PPT.md",
    "答辩/演示录屏说明.md",
    "输出样例/pca_主成分分析.csv",
    "输出样例/pca_主成分分析.json",
    "输出样例/pca_主成分分析.md",
    "输出样例/eval_log.txt",
)

MANUAL_ITEMS = (
    ("答辩 PPT", "答辩/答辩PPT.pptx", "当前可先使用答辩大纲，正式提交前需要制作 PPT。"),
    ("演示录屏", "答辩/演示录屏.mp4", "正式提交前需要录制 Streamlit/CLI 演示视频。"),
)
REQUIRED_ENV_KEYS = ("OPENAI_API_KEY",)

REQUIRED_CSV_FIELDS = (
    "platform",
    "title",
    "url",
    "author",
    "view",
    "like",
    "has_subtitle",
    "relevance",
    "depth",
    "clarity",
    "audience",
    "recommend",
    "reason",
)
REQUIRED_FULL_RUN_PLATFORMS = ("bilibili", "youtube")
SECRET_PATTERNS = (
    ("OpenAI API Key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z_-]{25,}\b")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("Bearer Token", re.compile(r"\bBearer\s+[A-Za-z0-9._-]{30,}\b")),
    ("Cookie/Session", re.compile(r"(?i)\b(cookie|session|token)\s*[:=]\s*[A-Za-z0-9%._-]{30,}\b")),
)
SECRET_ALLOWLIST_MARKERS = (
    "your_",
    "placeholder",
    "example",
    "fake",
    "for_test",
    "for-test",
    "should-not-print",
)
SECRET_SCAN_SKIP_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "cache",
    "node_modules",
    "pptx_unpacked",
    "docx_unpacked_read",
    "pptx_from_backup",
}
SECRET_SCAN_SKIP_SUFFIXES = {
    ".docx",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pyc",
    ".pyd",
    ".zip",
    ".mp4",
}
SECRET_SCAN_SKIP_NAMES = {".env"}


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_required_files() -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if path.exists() and path.stat().st_size > 0:
            results.append(CheckResult(relative, "pass", "文件存在且非空"))
        else:
            results.append(CheckResult(relative, "fail", "文件缺失或为空"))
    return results


def _check_no_mojibake() -> list[CheckResult]:
    targets = (
        "README.md",
        "goal.md",
        "prompts/eval_template.txt",
        "src/schema.py",
        "src/exporters.py",
        "文档/验收状态表.md",
        "文档/Prompt迭代记录.md",
        "文档/反思报告.md",
        "文档/终验运行记录.md",
    )
    results: list[CheckResult] = []
    for relative in targets:
        text = _read_text(ROOT / relative)
        markers = [marker for marker in MOJIBAKE_MARKERS if marker in text]
        if markers:
            results.append(CheckResult(relative, "fail", f"疑似乱码标记: {', '.join(markers)}"))
        else:
            results.append(CheckResult(relative, "pass", "未发现常见乱码标记"))
    return results


def _check_prompt_fields() -> list[CheckResult]:
    text = _read_text(ROOT / "prompts/eval_template.txt")
    required_fields = ("relevance", "depth", "clarity", "has_math", "has_code", "audience", "recommend", "reason")
    missing = [field for field in required_fields if field not in text]
    if missing:
        return [CheckResult("prompt fields", "fail", f"缺少字段: {', '.join(missing)}")]
    return [CheckResult("prompt fields", "pass", "Prompt 包含全部结构化评估字段")]


def _check_readme_reproducibility() -> list[CheckResult]:
    readme_text = _read_text(ROOT / "README.md")
    required_fragments = (
        "python -m pip install -r requirements.txt",
        "YOUTUBE_API_KEY=your_youtube_api_key",
        "OPENAI_API_KEY=your_openai_compatible_api_key",
        "DOUYIN_SAMPLE_JSON=",
        "代理配置",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "5 分钟本地验证",
        "正式终验复跑",
        "python scripts\\preflight_check.py",
        'python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30',
        "python scripts\\refresh_submission_samples.py",
        "python scripts\\acceptance_check.py --strict",
        "streamlit run app.py",
    )
    missing = _missing_fragments(readme_text, required_fragments)
    if missing:
        return [CheckResult("README 可复现性", "fail", f"缺少说明: {', '.join(missing)}")]
    return [CheckResult("README 可复现性", "pass", "安装、Key、代理、运行、UI、严格自检说明齐全")]


def _missing_fragments(text: str, fragments: tuple[str, ...]) -> list[str]:
    return [fragment for fragment in fragments if fragment not in text]


def _check_cli_contract() -> list[CheckResult]:
    main_text = _read_text(ROOT / "main.py")
    required_fragments = (
        "--platform",
        "bilibili,youtube,douyin or all",
        "--skip-evaluate",
        "--enable-asr",
        "--no-cache",
        "--clear-cache",
        "search_bilibili_videos",
        "search_youtube_videos",
        "search_douyin_videos",
        "evaluate_records",
        "export_results",
    )
    missing = _missing_fragments(main_text, required_fragments)
    if missing:
        return [CheckResult("CLI 功能入口", "fail", f"缺少片段: {', '.join(missing)}")]
    return [CheckResult("CLI 功能入口", "pass", "平台、评估、ASR、缓存和导出入口齐全")]


def _check_output_sample_contract() -> list[CheckResult]:
    csv_path = ROOT / "输出样例" / "pca_主成分分析.csv"
    json_path = ROOT / "输出样例" / "pca_主成分分析.json"
    md_path = ROOT / "输出样例" / "pca_主成分分析.md"
    log_path = ROOT / "输出样例" / "eval_log.txt"

    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader, [])
    missing_fields = [field for field in REQUIRED_CSV_FIELDS if field not in headers]

    try:
        json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        json_detail = f"JSON 解析失败: {exc}"
        json_status = "fail"
    else:
        json_status = "pass" if isinstance(json_payload, list) and json_payload else "fail"
        json_detail = f"记录数: {len(json_payload)}" if json_status == "pass" else "JSON 应为非空列表"

    markdown_text = _read_text(md_path)
    required_sections = ("入门理解层", "数学推导层", "代码实操层", "应用案例层", "推荐学习路径")
    missing_sections = _missing_fragments(markdown_text, required_sections)

    log_values = _parse_run_log(log_path)
    required_log_keys = (
        "total_records",
        "subtitle_success_count",
        "evaluation_success_count",
        "platform_counts",
        "subtitle_source_counts",
        "errors",
    )
    missing_log_keys = [key for key in required_log_keys if key not in log_values]

    results = [
        CheckResult(
            "输出样例 CSV 字段",
            "pass" if not missing_fields else "fail",
            "字段完整" if not missing_fields else f"缺少字段: {', '.join(missing_fields)}",
        ),
        CheckResult("输出样例 JSON", json_status, json_detail),
        CheckResult(
            "输出样例 Markdown 分层",
            "pass" if not missing_sections else "fail",
            "分层与学习路径完整" if not missing_sections else f"缺少分层: {', '.join(missing_sections)}",
        ),
        CheckResult(
            "输出样例运行日志",
            "pass" if not missing_log_keys else "fail",
            "运行统计键完整" if not missing_log_keys else f"缺少键: {', '.join(missing_log_keys)}",
        ),
    ]
    return results


def _check_engineering_contracts() -> list[CheckResult]:
    main_text = _read_text(ROOT / "main.py")
    app_text = _read_text(ROOT / "app.py")
    verify_streamlit_text = _read_text(ROOT / "scripts/verify_streamlit_ui.py")
    asr_text = _read_text(ROOT / "src/asr_whisper.py")
    verify_asr_text = _read_text(ROOT / "scripts/verify_asr.py")
    cache_text = _read_text(ROOT / "src/cache_utils.py")
    verify_cache_text = _read_text(ROOT / "scripts/verify_cache.py")
    douyin_text = _read_text(ROOT / "src/search_douyin.py")
    douyin_doc_text = _read_text(ROOT / "文档/抖音抓取降级说明与工程代价对比.md")
    refresh_samples_text = _read_text(ROOT / "scripts/refresh_submission_samples.py")
    preflight_text = _read_text(ROOT / "scripts/preflight_check.py")
    youtube_text = _read_text(ROOT / "src/search_youtube.py")
    package_submission_text = _read_text(ROOT / "scripts/package_submission.py")
    final_audit_text = _read_text(ROOT / "scripts/final_audit.py")
    demo_recording_text = _read_text(ROOT / "scripts/generate_demo_recording.py")
    run_final_acceptance_text = _read_text(ROOT / "scripts/run_final_acceptance.py")
    gitignore_text = _read_text(ROOT / ".gitignore")
    env_example_text = _read_text(ROOT / ".env.example")
    requirements_text = _read_text(ROOT / "requirements.txt")

    cache_missing = _missing_fragments(
        cache_text + main_text,
        ("load_json_cache", "save_json_cache", "clear_cache", "--no-cache", "--clear-cache"),
    )
    verify_cache_missing = _missing_fragments(
        verify_cache_text,
        (
            "verify_cache",
            "miss_before_save",
            "hit_after_save",
            "miss_after_clear",
            "SELF_CHECK_NAMESPACE",
            "cache_utils.clear_cache",
            "cache_utils.save_json_cache",
            "cache_utils.load_json_cache",
        ),
    )
    asr_missing = _missing_fragments(
        asr_text,
        (
            "ASR_MODEL",
            "ASR_COMPUTE_TYPE",
            "ASR_DEVICE",
            "TemporaryDirectory",
            "whisper_asr",
            "yt_dlp",
            "faster_whisper",
        ),
    )
    verify_asr_missing = _missing_fragments(
        verify_asr_text,
        (
            "verify_asr_environment",
            "yt_dlp_available",
            "faster_whisper_available",
            "ASR_MODEL",
            "ASR_COMPUTE_TYPE",
            "ASR_DEVICE",
            "DEFAULT_ASR_MODEL",
            "DEFAULT_ASR_COMPUTE_TYPE",
            "DEFAULT_ASR_DEVICE",
            "without downloading models",
        ),
    )
    douyin_missing = _missing_fragments(
        douyin_text + main_text,
        ("DOUYIN_SAMPLE_JSON", "DEFAULT_REFERENCE_JSON", 'platform="douyin"', "播放数", "点赞数", "douyin"),
    )
    douyin_doc_missing = _missing_fragments(
        douyin_doc_text,
        (
            "python main.py --topic",
            "--platform douyin",
            "DOUYIN_SAMPLE_JSON",
            "降级方案",
            "工程代价对比",
            "人工登录",
            "风控",
            "统一 VideoRecord",
        ),
    )
    ui_missing = _missing_fragments(
        app_text,
        (
            "学习主题",
            "检索平台",
            "跳过 LLM 评估",
            "启用 ASR 兜底",
            "YouTube API Key",
            "OpenAI compatible API Key",
            "OpenAI compatible Base URL",
            "本地代理端口",
            "下载 CSV",
            "下载 Markdown",
        ),
    )
    ui_smoke_missing = _missing_fragments(
        verify_streamlit_text,
        (
            "verify_streamlit_ui",
            "build_streamlit_command",
            "streamlit",
            "--server.headless",
            "--server.port",
            "HTTP 200",
            "urlopen",
            "process.terminate",
        ),
    )
    gitignore_missing = _missing_fragments(gitignore_text, (".env", ".venv/", "results/", "__pycache__/", "提交包/"))
    env_missing = _missing_fragments(
        env_example_text,
        (
            "YOUTUBE_API_KEY=your_youtube_api_key",
            "OPENAI_API_KEY=your_openai_compatible_api_key",
            "OPENAI_BASE_URL=",
            "OPENAI_MODEL=",
            "ASR_MODEL=",
            "ASR_COMPUTE_TYPE=",
            "ASR_DEVICE=",
            "DOUYIN_SAMPLE_JSON=",
        ),
    )
    dependency_missing = _missing_fragments(
        requirements_text,
        (
            "google-api-python-client",
            "openai",
            "faster-whisper",
            "yt-dlp",
            "streamlit",
            "youtube-transcript-api",
            "bilibili-api-python",
            "pytest",
            "ruff",
            "black",
        ),
    )
    refresh_samples_missing = _missing_fragments(
        refresh_samples_text,
        (
            "refresh_submission_samples",
            "REQUIRED_CSV_FIELDS",
            "required_platforms",
            "min_records",
            "min_evaluation_ratio",
            "pca_主成分分析",
            "eval_log.txt",
            "shutil.copy2",
            "total_records",
            "evaluation_success_count",
            "CSV missing required platform",
            "CSV missing required field",
        ),
    )
    preflight_missing = _missing_fragments(
        preflight_text,
        (
            "run_preflight",
            "YOUTUBE_API_KEY",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_MODEL",
            "HTTP_PROXY",
            "DOUYIN_SAMPLE_JSON",
            "length=",
            "缺失或仍为占位符",
        ),
    )
    youtube_fallback_missing = _missing_fragments(
        youtube_text,
        (
            "YoutubeDL",
            "ytsearch",
            "_search_with_ytdlp",
            "Missing YOUTUBE_API_KEY; falling back to yt-dlp YouTube search",
            "YouTube Data API search failed; falling back to yt-dlp",
        ),
    )
    package_submission_missing = _missing_fragments(
        package_submission_text,
        (
            "create_submission_package",
            "INCLUDE_PATHS",
            "EXCLUDE_DIRS",
            "EXCLUDE_FILE_NAMES",
            "zipfile.ZipFile",
            "README.md",
            "文档",
            "评估表",
            "答辩",
            "输出样例",
            ".env",
            ".venv",
            "results",
        ),
    )
    final_audit_missing = _missing_fragments(
        final_audit_text,
        (
            "generate_final_audit_markdown",
            "write_final_audit_report",
            "run_acceptance_checks",
            "DEFAULT_OUTPUT",
            "终验审计报告",
            "状态汇总",
            "待补齐项",
            "Generated final audit report",
        ),
    )
    demo_recording_missing = _missing_fragments(
        demo_recording_text,
        (
            "generate_demo_recording",
            "build_drawtext_filter",
            "build_ffmpeg_command",
            "DEMO_SEGMENTS",
            "ffmpeg",
            "演示录屏.mp4",
            "本视频不伪造外部 API 运行结果",
            "Generated demo recording",
        ),
    )
    run_final_acceptance_missing = _missing_fragments(
        run_final_acceptance_text,
        (
            "build_final_acceptance_steps",
            "run_final_acceptance",
            "--dry-run",
            "scripts/preflight_check.py",
            "main.py",
            "bilibili,youtube",
            "scripts/refresh_submission_samples.py",
            "scripts/acceptance_check.py",
            "--strict",
            "scripts/package_submission.py",
        ),
    )
    secret_markers = ("sk-", "AIza", "Bearer ", "xoxb-", "ghp_")
    leaked_secret_markers = [marker for marker in secret_markers if marker in env_example_text]

    return [
        CheckResult(
            "缓存契约",
            "pass" if not cache_missing else "fail",
            "搜索/字幕/评估缓存工具和 CLI 开关齐全" if not cache_missing else f"缺少片段: {', '.join(cache_missing)}",
        ),
        CheckResult(
            "缓存自检工具",
            "pass" if not verify_cache_missing else "fail",
            (
                "可离线验证缓存未命中、写入命中和清理后未命中"
                if not verify_cache_missing
                else f"缺少片段: {', '.join(verify_cache_missing)}"
            ),
        ),
        CheckResult(
            "ASR 契约",
            "pass" if not asr_missing else "fail",
            (
                "支持模型环境变量、临时目录清理和 whisper_asr 回填"
                if not asr_missing
                else f"缺少片段: {', '.join(asr_missing)}"
            ),
        ),
        CheckResult(
            "ASR 环境自检工具",
            "pass" if not verify_asr_missing else "fail",
            (
                "可检查 yt-dlp、faster-whisper 和 ASR 默认配置且不下载模型"
                if not verify_asr_missing
                else f"缺少片段: {', '.join(verify_asr_missing)}"
            ),
        ),
        CheckResult(
            "抖音整合契约",
            "pass" if not douyin_missing else "fail",
            "支持参考 JSON 与统一 VideoRecord 输出" if not douyin_missing else f"缺少片段: {', '.join(douyin_missing)}",
        ),
        CheckResult(
            "抖音降级说明",
            "pass" if not douyin_doc_missing else "fail",
            (
                "包含可运行降级命令、环境变量、登录/风控边界和工程代价对比"
                if not douyin_doc_missing
                else f"缺少片段: {', '.join(douyin_doc_missing)}"
            ),
        ),
        CheckResult(
            "Streamlit UI 契约",
            "pass" if not ui_missing else "fail",
            (
                "主题、平台、评估、ASR、Key、代理和下载控件齐全"
                if not ui_missing
                else f"缺少控件: {', '.join(ui_missing)}"
            ),
        ),
        CheckResult(
            "Streamlit UI 自检工具",
            "pass" if not ui_smoke_missing else "fail",
            (
                "可启动 headless Streamlit 并验证本地 HTTP 200"
                if not ui_smoke_missing
                else f"缺少片段: {', '.join(ui_smoke_missing)}"
            ),
        ),
        CheckResult(
            "Git 忽略规则",
            "pass" if not gitignore_missing else "fail",
            (
                "已忽略密钥、虚拟环境、结果、提交包和缓存目录"
                if not gitignore_missing
                else f"缺少规则: {', '.join(gitignore_missing)}"
            ),
        ),
        CheckResult(
            ".env.example 安全性",
            "pass" if not env_missing and not leaked_secret_markers else "fail",
            (
                "仅包含占位符和必要环境变量"
                if not env_missing and not leaked_secret_markers
                else f"缺少变量: {', '.join(env_missing)}; 疑似密钥标记: {', '.join(leaked_secret_markers)}"
            ),
        ),
        _check_secret_scan()[0],
        CheckResult(
            "依赖覆盖",
            "pass" if not dependency_missing else "fail",
            "核心、测试和加分项依赖齐全" if not dependency_missing else f"缺少依赖: {', '.join(dependency_missing)}",
        ),
        CheckResult(
            "提交样例刷新工具",
            "pass" if not refresh_samples_missing else "fail",
            (
                "可校验最终 run log、CSV 字段和平台覆盖，并刷新 CSV/JSON/Markdown/log 样例"
                if not refresh_samples_missing
                else f"缺少片段: {', '.join(refresh_samples_missing)}"
            ),
        ),
        CheckResult(
            "终验前置检查工具",
            "pass" if not preflight_missing else "fail",
            (
                "可检查 .env、必要 Key、代理和抖音参考 JSON，且不输出密钥原文"
                if not preflight_missing
                else f"缺少片段: {', '.join(preflight_missing)}"
            ),
        ),
        CheckResult(
            "YouTube 无 Key 降级契约",
            "pass" if not youtube_fallback_missing else "fail",
            (
                "缺少 YOUTUBE_API_KEY 或 Data API 失败时可尝试 yt-dlp 搜索降级"
                if not youtube_fallback_missing
                else f"缺少片段: {', '.join(youtube_fallback_missing)}"
            ),
        ),
        CheckResult(
            "提交包工具",
            "pass" if not package_submission_missing else "fail",
            (
                "可打包 README、文档、评估表、答辩和输出样例，并排除密钥/虚拟环境/运行结果"
                if not package_submission_missing
                else f"缺少片段: {', '.join(package_submission_missing)}"
            ),
        ),
        CheckResult(
            "终验审计报告工具",
            "pass" if not final_audit_missing else "fail",
            (
                "可汇总 acceptance_check 结果并生成终验审计 Markdown 报告"
                if not final_audit_missing
                else f"缺少片段: {', '.join(final_audit_missing)}"
            ),
        ),
        CheckResult(
            "演示录屏生成工具",
            "pass" if not demo_recording_missing else "fail",
            (
                "可用 ffmpeg 生成可复现演示 MP4，并明确标注外部 API 复跑边界"
                if not demo_recording_missing
                else f"缺少片段: {', '.join(demo_recording_missing)}"
            ),
        ),
        CheckResult(
            "终验复跑编排工具",
            "pass" if not run_final_acceptance_missing else "fail",
            (
                "可按 preflight、双平台运行、样例刷新、严格自检、审计报告、演示视频和提交包顺序编排终验复跑"
                if not run_final_acceptance_missing
                else f"缺少片段: {', '.join(run_final_acceptance_missing)}"
            ),
        ),
    ]


def _should_scan_file(path: Path) -> bool:
    if path.name in SECRET_SCAN_SKIP_NAMES:
        return False
    if path.suffix.lower() in SECRET_SCAN_SKIP_SUFFIXES:
        return False
    return not any(part in SECRET_SCAN_SKIP_DIRS for part in path.relative_to(ROOT).parts[:-1])


def _is_allowed_secret_match(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in SECRET_ALLOWLIST_MARKERS)


def _iter_text_files_for_secret_scan() -> list[Path]:
    files: list[Path] = []
    stack = [ROOT]
    while stack:
        directory = stack.pop()
        try:
            children = list(directory.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name not in SECRET_SCAN_SKIP_DIRS:
                    stack.append(child)
                continue
            if child.is_file() and _should_scan_file(child):
                files.append(child)
    return files


def _check_secret_scan() -> list[CheckResult]:
    findings: list[str] = []
    for path in _iter_text_files_for_secret_scan():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT)
        for line_number, line in enumerate(lines, start=1):
            if _is_allowed_secret_match(line):
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{relative}:{line_number} ({label})")

    if findings:
        return [
            CheckResult(
                "仓库密钥扫描",
                "fail",
                "疑似密钥位置: " + "；".join(findings[:10]),
            )
        ]
    return [CheckResult("仓库密钥扫描", "pass", "未发现 OpenAI/Google/GitHub/Bearer/Cookie 等常见密钥形态")]


def _check_submission_materials() -> list[CheckResult]:
    docs_readme_text = _read_text(ROOT / "文档/README.md")
    report_text = _read_text(ROOT / "文档/反思报告.md")
    prompt_text = _read_text(ROOT / "文档/Prompt迭代记录.md")
    evaluation_text = _read_text(ROOT / "评估表/人工对照评估结果.md")
    audit_report_path = ROOT / "文档/终验审计报告.md"
    audit_report_text = audit_report_path.read_text(encoding="utf-8") if audit_report_path.exists() else ""
    docs_readme_missing = _missing_fragments(
        docs_readme_text,
        (
            "根目录开发版",
            "README.md",
            "输出样例",
            "评估表",
            "答辩",
            "Week01_周报",
            "Week04_周报",
            "python scripts\\acceptance_check.py",
            "python scripts\\final_audit.py",
            "终验审计报告",
        ),
    )
    audit_report_missing = _missing_fragments(
        audit_report_text,
        (
            "# 终验审计报告",
            "生成时间：",
            "## 状态汇总",
            "## 通过项",
            "## 待补齐项",
            "| status | count |",
        ),
    )
    results = [
        CheckResult(
            "文档提交清单",
            "pass" if not docs_readme_missing else "fail",
            (
                "覆盖运行基准、文档/输出/评估/答辩材料和自检命令"
                if not docs_readme_missing
                else f"缺少片段: {', '.join(docs_readme_missing)}"
            ),
        ),
        CheckResult("反思报告长度", "pass" if len(report_text) >= 1500 else "fail", f"当前字符数: {len(report_text)}"),
        CheckResult(
            "Prompt 迭代版本",
            "pass" if all(v in prompt_text for v in ("V1", "V2", "V3")) else "fail",
            "需要包含 V1/V2/V3",
        ),
        CheckResult(
            "人工对照一致率",
            "pass" if "80%" in evaluation_text and "达标" in evaluation_text else "fail",
            "需要记录 ≥70% 且达标",
        ),
        CheckResult(
            "终验审计报告文档",
            "pass" if audit_report_path.exists() and not audit_report_missing else "fail",
            (
                "包含生成时间、状态汇总、通过项和待补齐项"
                if audit_report_path.exists() and not audit_report_missing
                else f"缺少片段: {', '.join(audit_report_missing) or '文档不存在'}"
            ),
        ),
    ]
    return results


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _check_root_env() -> list[CheckResult]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return [
            CheckResult(
                "根目录 .env",
                "warn",
                "需要创建本地 .env，并填入真实 YOUTUBE_API_KEY 和 OPENAI_API_KEY 后复跑完整链路。",
            )
        ]

    env_values = _parse_env_file(env_path)
    missing_keys = [key for key in REQUIRED_ENV_KEYS if not is_real_env_value(env_values.get(key))]
    if missing_keys:
        return [
            CheckResult(
                "根目录 .env",
                "warn",
                "已找到本地 .env，但仍需填入真实 " + ", ".join(missing_keys) + " 后复跑完整链路。",
            )
        ]
    if not is_real_env_value(env_values.get("YOUTUBE_API_KEY")):
        return [
            CheckResult(
                "根目录 .env",
                "pass",
                "已找到本地 .env，OPENAI_API_KEY 已配置；YOUTUBE_API_KEY 未配置时将使用 yt-dlp 降级搜索。",
            )
        ]
    return [
        CheckResult(
            "根目录 .env",
            "pass",
            "已找到本地 .env，且必要 Key 已配置；自检不输出密钥原文。",
        )
    ]


def _check_manual_items() -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, relative, detail in MANUAL_ITEMS:
        path = ROOT / relative
        if path.exists() and path.stat().st_size > 0:
            results.append(CheckResult(name, "pass", f"已找到: {relative}"))
        else:
            results.append(CheckResult(name, "warn", detail))
    return results


def _parse_run_log(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _read_int_value(values: dict[str, str], key: str) -> int:
    try:
        return int(values.get(key, "0") or 0)
    except ValueError:
        return 0


def _read_csv_headers_and_platforms(path: Path) -> tuple[list[str], set[str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = list(reader.fieldnames or [])
        platforms = {str(row.get("platform", "")).strip().lower() for row in reader}
    return headers, platforms


def _check_full_run_artifacts() -> list[CheckResult]:
    log_path = ROOT / "results" / "PCA_主成分分析_run.log"
    csv_path = ROOT / "results" / "PCA_主成分分析.csv"
    json_path = ROOT / "results" / "PCA_主成分分析.json"
    md_path = ROOT / "results" / "PCA_主成分分析.md"
    required_paths = (csv_path, json_path, md_path, log_path)
    issues: list[str] = []
    for path in required_paths:
        if path.exists() and path.stat().st_size > 0:
            continue
        if path == json_path:
            issues.append("JSON 文件缺失或为空")
        else:
            issues.append(f"{path.name} 缺失或为空")
    if issues:
        return [
            CheckResult(
                "双平台 30 条完整输出",
                "warn",
                "需要完成真实双平台复跑后生成完整结果；YouTube 可使用官方 API Key 或 yt-dlp 降级：" + "；".join(issues),
            )
        ]

    values = _parse_run_log(log_path)
    total_records = _read_int_value(values, "total_records")
    evaluation_success_count = _read_int_value(values, "evaluation_success_count")
    if total_records < 30:
        issues.append(f"total_records={total_records} < 30")
    if evaluation_success_count < 27:
        issues.append(f"evaluation_success_count={evaluation_success_count} < 27")

    headers, platforms = _read_csv_headers_and_platforms(csv_path)
    missing_fields = [field for field in REQUIRED_CSV_FIELDS if field not in headers]
    if missing_fields:
        issues.append(f"CSV 缺少字段: {', '.join(missing_fields)}")
    missing_platforms = [platform for platform in REQUIRED_FULL_RUN_PLATFORMS if platform not in platforms]
    if missing_platforms:
        issues.append(f"CSV missing required platform(s): {', '.join(missing_platforms)}")

    try:
        json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"JSON 解析失败: {exc}")
    else:
        if not isinstance(json_payload, list):
            issues.append("JSON 应为列表")
        elif len(json_payload) < 30:
            issues.append(f"JSON 记录数={len(json_payload)} < 30")

    if not issues:
        return [
            CheckResult(
                "双平台 30 条完整输出",
                "pass",
                f"total_records={total_records}, evaluation_success_count={evaluation_success_count}",
            )
        ]
    return [
        CheckResult(
            "双平台 30 条完整输出",
            "warn",
            "需要完成 B 站 + YouTube 30 条真实 CSV/JSON/Markdown/run log；YouTube 可使用官方 API Key 或 yt-dlp 降级："
            + "；".join(issues),
        )
    ]


def run_acceptance_checks(*, strict: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(_check_required_files())
    results.extend(_check_no_mojibake())
    results.extend(_check_prompt_fields())
    results.extend(_check_readme_reproducibility())
    results.extend(_check_cli_contract())
    results.extend(_check_output_sample_contract())
    results.extend(_check_engineering_contracts())
    results.extend(_check_submission_materials())
    results.extend(_check_root_env())
    results.extend(_check_manual_items())
    results.extend(_check_full_run_artifacts())
    if strict:
        results = [
            CheckResult(item.name, "fail" if item.status == "warn" else item.status, item.detail) for item in results
        ]
    return results


def _print_table(results: list[CheckResult]) -> None:
    for item in results:
        print(f"[{item.status.upper()}] {item.name}: {item.detail}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run offline final-acceptance checks for the project.")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")
    parser.add_argument("--strict", action="store_true", help="Treat manual warning items as failures")
    args = parser.parse_args()

    results = run_acceptance_checks(strict=args.strict)
    if args.json:
        print(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))
    else:
        _print_table(results)

    return 1 if any(item.status == "fail" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
