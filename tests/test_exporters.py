from src.exporters import export_markdown, export_run_log
from src.schema import SearchSummary, VideoRecord


def test_export_markdown_uses_readable_chinese_sections(tmp_path):
    path = tmp_path / "pca.md"
    records = [
        VideoRecord(
            platform="bilibili",
            video_id="BV1xx411c7mD",
            title="PCA 主成分分析讲解",
            url="https://www.bilibili.com/video/BV1xx411c7mD",
            author="测试作者",
            view=1000,
            duration=300,
            audience="本科入门",
            recommend="yes",
            reason="讲解清楚，适合作为入门材料。",
        )
    ]
    summary = SearchSummary(
        total_records=1,
        evaluation_success_count=1,
        evaluation_success_ratio=1.0,
        platform_counts={"bilibili": 1},
        subtitle_source_counts={"whisper_asr": 1},
    )

    export_markdown(path, "PCA 主成分分析", records, summary)

    content = path.read_text(encoding="utf-8")
    assert "# PCA 主成分分析 学习资源推荐" in content
    assert "## 入门理解层" in content
    assert "## 数学推导层" in content
    assert "## 代码实操层" in content
    assert "## 应用案例层" in content
    assert "讲解清楚，适合作为入门材料。" in content
    assert "平台分布：bilibili:1" in content
    assert "字幕来源分布：whisper_asr:1" in content


def test_export_run_log_includes_platform_and_subtitle_source_counts(tmp_path):
    path = tmp_path / "run.log"
    summary = SearchSummary(
        total_records=2,
        subtitle_success_count=2,
        subtitle_success_ratio=1.0,
        evaluation_success_count=2,
        evaluation_success_ratio=1.0,
        platform_counts={"youtube": 1, "bilibili": 1},
        subtitle_source_counts={"whisper_asr": 1, "youtube_transcript": 1},
    )

    export_run_log(path, "PCA 主成分分析", summary)

    content = path.read_text(encoding="utf-8")
    assert "platform_counts=bilibili:1,youtube:1" in content
    assert "subtitle_source_counts=whisper_asr:1,youtube_transcript:1" in content
