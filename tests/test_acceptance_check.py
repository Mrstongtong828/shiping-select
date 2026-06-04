import json
from pathlib import Path

from scripts import acceptance_check
from scripts.acceptance_check import run_acceptance_checks


def test_acceptance_check_has_no_offline_failures():
    results = run_acceptance_checks()

    failures = [item for item in results if item.status == "fail"]
    assert failures == []


def test_acceptance_check_keeps_manual_items_as_warnings():
    results = run_acceptance_checks()

    result_by_name = {item.name: item for item in results}
    warning_names = {item.name for item in results if item.status == "warn"}
    assert result_by_name["根目录 .env"].status in {"pass", "warn"}
    assert result_by_name["双平台 30 条完整输出"].status in {"pass", "warn"}
    assert "答辩 PPT" not in warning_names
    assert "演示录屏" not in warning_names


def test_root_env_warns_when_file_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_root_env()

    assert result.status == "warn"
    assert ".env" in result.detail


def test_root_env_warns_when_openai_key_is_placeholder(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "YOUTUBE_API_KEY=fake-youtube-key-for-test",
                "OPENAI_API_KEY=your_openai_compatible_api_key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_root_env()

    assert result.status == "warn"
    assert "OPENAI_API_KEY" in result.detail
    assert "fake-youtube-key-for-test" not in result.detail


def test_root_env_passes_with_youtube_fallback_when_openai_is_configured(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "YOUTUBE_API_KEY=your_youtube_api_key",
                "OPENAI_API_KEY=fake-openai-key-for-test",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_root_env()

    assert result.status == "pass"
    assert "yt-dlp" in result.detail
    assert "fake-openai-key-for-test" not in result.detail


def test_root_env_passes_when_required_keys_are_configured(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "YOUTUBE_API_KEY=fake-youtube-key-for-test",
                "OPENAI_API_KEY=fake-openai-key-for-test",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_root_env()

    assert result.status == "pass"
    assert "fake-youtube-key-for-test" not in result.detail
    assert "fake-openai-key-for-test" not in result.detail


def test_acceptance_check_covers_implemented_contracts():
    results = {item.name: item for item in run_acceptance_checks()}

    expected_passes = (
        "README 可复现性",
        "CLI 功能入口",
        "输出样例 CSV 字段",
        "输出样例 JSON",
        "输出样例 Markdown 分层",
        "输出样例运行日志",
        "缓存契约",
        "缓存自检工具",
        "ASR 契约",
        "ASR 环境自检工具",
        "抖音整合契约",
        "抖音降级说明",
        "Streamlit UI 契约",
        "Streamlit UI 自检工具",
        "Git 忽略规则",
        ".env.example 安全性",
        "仓库密钥扫描",
        "依赖覆盖",
        "提交样例刷新工具",
        "终验前置检查工具",
        "YouTube 无 Key 降级契约",
        "文档提交清单",
        "提交包工具",
        "终验审计报告工具",
        "终验审计报告文档",
        "演示录屏生成工具",
        "终验复跑编排工具",
        "演示录屏",
    )
    for name in expected_passes:
        assert results[name].status == "pass"


def test_secret_scan_flags_obvious_openai_key(monkeypatch, tmp_path):
    (tmp_path / "README.md").write_text("OPENAI_API_KEY=sk-" + "a" * 48, encoding="utf-8")
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_secret_scan()

    assert result.status == "fail"
    assert "README.md" in result.detail
    assert "sk-" not in result.detail


def _write_full_run_artifacts(root: Path, *, platforms: tuple[str, ...], include_json: bool = True) -> None:
    results_dir = root / "results"
    results_dir.mkdir()
    header = "platform,title,url,author,view,like,has_subtitle,relevance,depth,clarity," "audience,recommend,reason\n"
    rows = [
        f"{platform},样例 {index},https://example.com/{index},作者,100,10,true,8,7,8,本科入门,yes,理由\n"
        for index, platform in enumerate(platforms, start=1)
    ]
    (results_dir / "PCA_主成分分析.csv").write_text(header + "".join(rows), encoding="utf-8")
    if include_json:
        payload = [
            {
                "platform": platform,
                "title": f"样例 {index}",
                "url": f"https://example.com/{index}",
            }
            for index, platform in enumerate(platforms, start=1)
        ]
        while len(payload) < 30:
            payload.append(payload[-1] | {"title": f"样例 {len(payload) + 1}"})
        (results_dir / "PCA_主成分分析.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    (results_dir / "PCA_主成分分析.md").write_text("# PCA 主成分分析 学习资源推荐\n", encoding="utf-8")
    (results_dir / "PCA_主成分分析_run.log").write_text(
        "\n".join(
            [
                "topic=PCA 主成分分析",
                "total_records=30",
                "subtitle_success_count=24",
                "subtitle_success_ratio=0.8000",
                "evaluation_success_count=28",
                "evaluation_success_ratio=0.9333",
                "platform_counts=bilibili:1,youtube:1",
                "subtitle_source_counts=whisper_asr:1,youtube_transcript:1",
                "errors=0",
            ]
        ),
        encoding="utf-8",
    )


def test_full_run_artifacts_require_json(monkeypatch, tmp_path):
    _write_full_run_artifacts(tmp_path, platforms=("bilibili", "youtube"), include_json=False)
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_full_run_artifacts()

    assert result.status == "warn"
    assert "JSON" in result.detail


def test_full_run_artifacts_require_dual_platform(monkeypatch, tmp_path):
    _write_full_run_artifacts(tmp_path, platforms=("bilibili",))
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_full_run_artifacts()

    assert result.status == "warn"
    assert "youtube" in result.detail


def test_full_run_artifacts_pass_for_valid_dual_platform_run(monkeypatch, tmp_path):
    _write_full_run_artifacts(tmp_path, platforms=("bilibili", "youtube"))
    monkeypatch.setattr(acceptance_check, "ROOT", tmp_path)

    [result] = acceptance_check._check_full_run_artifacts()

    assert result.status == "pass"
    assert "total_records=30" in result.detail
