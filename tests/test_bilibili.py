from src.schema import VideoRecord


def test_video_record_accepts_bilibili_payload():
    record = VideoRecord(
        platform="bilibili",
        video_id="BV1xx411c7mD",
        title="PCA 主成分分析讲解",
        url="https://www.bilibili.com/video/BV1xx411c7mD",
        has_subtitle=True,
        subtitle_text="这是字幕",
    )

    assert record.platform == "bilibili"
    assert record.has_subtitle is True
    assert record.subtitle_text == "这是字幕"
