import pytest

from main import build_summary, normalize_platforms, slugify_topic
from src.schema import VideoRecord


def test_normalize_platforms_expands_all():
    assert normalize_platforms(["all"]) == ["bilibili", "youtube", "douyin"]


def test_normalize_platforms_deduplicates_and_keeps_order():
    assert normalize_platforms(["youtube", "bilibili", "youtube"]) == ["youtube", "bilibili"]


def test_normalize_platforms_rejects_unknown_platform():
    with pytest.raises(ValueError, match="Unsupported platform"):
        normalize_platforms(["bilibili", "unknown"])


def test_slugify_topic_keeps_chinese_topic():
    assert slugify_topic("PCA 主成分分析") == "PCA_主成分分析"


def test_build_summary_counts_platforms_and_subtitle_sources():
    records = [
        VideoRecord(
            platform="bilibili",
            video_id="BV1",
            title="B 站 PCA",
            url="https://www.bilibili.com/video/BV1",
            has_subtitle=True,
            subtitle_source="bilibili",
            recommend="yes",
        ),
        VideoRecord(
            platform="youtube",
            video_id="yt1",
            title="YouTube PCA",
            url="https://www.youtube.com/watch?v=yt1",
            has_subtitle=True,
            subtitle_source="whisper_asr",
            recommend="no",
        ),
    ]

    summary = build_summary(records, errors=[])

    assert summary.platform_counts == {"bilibili": 1, "youtube": 1}
    assert summary.subtitle_source_counts == {"bilibili": 1, "whisper_asr": 1}
    assert summary.evaluation_success_count == 2
