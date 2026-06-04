import os

import app
from src.schema import SearchSummary, VideoRecord


def test_set_env_if_value_skips_empty(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    app._set_env_if_value("OPENAI_MODEL", "   ")

    assert "OPENAI_MODEL" not in os.environ


def test_set_env_if_value_sets_non_empty(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    app._set_env_if_value("OPENAI_MODEL", "deepseek-chat")

    assert os.environ["OPENAI_MODEL"] == "deepseek-chat"


def test_set_env_if_value_skips_placeholder(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    app._set_env_if_value("OPENAI_API_KEY", "your_openai_compatible_api_key")

    assert "OPENAI_API_KEY" not in os.environ


def test_set_env_if_value_skips_quoted_placeholder(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    app._set_env_if_value("YOUTUBE_API_KEY", ' "your_youtube_api_key" ')

    assert "YOUTUBE_API_KEY" not in os.environ


def test_configure_proxy_sets_standard_proxy_env(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.delenv(name, raising=False)

    app._configure_proxy("7890")

    assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:7890"
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:7890"
    assert os.environ["ALL_PROXY"] == "http://127.0.0.1:7890"


def _record(title, **kwargs):
    return VideoRecord(
        platform="bilibili",
        video_id=title,
        title=title,
        url=f"https://example.com/{title}",
        **kwargs,
    )


def test_bucket_learning_records_groups_results_into_four_learning_layers():
    buckets = app._bucket_learning_records(
        [
            _record("code", has_code=True),
            _record("math", has_math=True, depth=8),
            _record("case", description="应用案例演示", depth=6),
            _record("intro", depth=2),
        ]
    )

    assert [record.title for record in buckets["代码实操层"]] == ["code"]
    assert [record.title for record in buckets["数学推导层"]] == ["math"]
    assert [record.title for record in buckets["应用案例层"]] == ["case"]
    assert [record.title for record in buckets["入门理解层"]] == ["intro"]


def test_build_overview_metrics_formats_summary_counts():
    metrics = app._build_overview_metrics(
        SearchSummary(
            total_records=30,
            subtitle_success_count=21,
            subtitle_success_ratio=0.7,
            evaluation_success_count=27,
            evaluation_success_ratio=0.9,
            platform_counts={"youtube": 12, "bilibili": 18},
            subtitle_source_counts={"transcript": 10, "bilibili": 11},
        )
    )

    assert metrics["total_records"] == "30"
    assert metrics["subtitle_success"] == "21 / 70%"
    assert metrics["evaluation_success"] == "27 / 90%"
    assert metrics["platform_distribution"] == "bilibili:18, youtube:12"
    assert metrics["subtitle_source_distribution"] == "bilibili:11, transcript:10"
