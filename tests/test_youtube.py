import pytest

from src import search_youtube
from src.schema import SubtitlePayload


def test_fetch_transcript_uses_current_youtube_transcript_api(monkeypatch):
    class FakeTranscript:
        language_code = "en"

        def fetch(self):
            return object()

    class FakeTranscriptList:
        def find_transcript(self, languages):
            assert languages == ["zh-Hans", "zh-CN", "zh", "en"]
            return FakeTranscript()

    class FakeTranscriptApi:
        def list(self, video_id):
            assert video_id == "video-1"
            return FakeTranscriptList()

    class FakeFormatter:
        def format_transcript(self, data):
            return "hello transcript"

    monkeypatch.setattr(search_youtube, "YouTubeTranscriptApi", FakeTranscriptApi)
    monkeypatch.setattr(search_youtube, "TextFormatter", FakeFormatter)

    subtitle = search_youtube._fetch_transcript("video-1", subtitle_limit=5, use_cache=False)

    assert subtitle.text == "hello"
    assert subtitle.language == "en"
    assert subtitle.source == "youtube_transcript"


def test_build_youtube_client_rejects_placeholder_key(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "your_youtube_api_key")

    with pytest.raises(RuntimeError, match="Missing YOUTUBE_API_KEY"):
        search_youtube._build_youtube_client()


class FakeYoutubeDL:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def extract_info(self, query, download):
        assert query == "ytsearch2:PCA 主成分分析"
        assert download is False
        return {
            "entries": [
                {
                    "id": "video-1",
                    "title": "PCA 教程",
                    "webpage_url": "https://www.youtube.com/watch?v=video-1",
                    "channel": "统计老师",
                    "view_count": "1000",
                    "like_count": "50",
                    "duration": "600",
                    "upload_date": "20240501",
                }
            ]
        }


def test_search_sync_falls_back_to_ytdlp_without_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.setattr(search_youtube, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(
        search_youtube,
        "_fetch_transcript",
        lambda video_id, subtitle_limit, use_cache: SubtitlePayload(
            text="transcript",
            language="en",
            source="youtube_transcript",
        ),
    )

    records = search_youtube._search_sync(
        topic="PCA 主成分分析",
        limit=2,
        subtitle_limit=100,
        enable_asr=False,
        use_cache=False,
    )

    assert len(records) == 1
    assert records[0].platform == "youtube"
    assert records[0].video_id == "video-1"
    assert records[0].title == "PCA 教程"
    assert records[0].author == "统计老师"
    assert records[0].view == 1000
    assert records[0].like == 50
    assert records[0].duration == 600
    assert records[0].publish_time == "2024-05-01T00:00:00Z"
    assert records[0].has_subtitle is True


def test_search_sync_falls_back_to_ytdlp_when_data_api_fails(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "real-youtube-key-for-test")
    monkeypatch.setattr(search_youtube, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(
        search_youtube,
        "_search_with_data_api",
        lambda topic, limit, subtitle_limit, enable_asr, use_cache: (_ for _ in ()).throw(RuntimeError("quota")),
    )
    monkeypatch.setattr(
        search_youtube,
        "_fetch_transcript",
        lambda video_id, subtitle_limit, use_cache: SubtitlePayload(),
    )

    records = search_youtube._search_sync(
        topic="PCA 主成分分析",
        limit=2,
        subtitle_limit=100,
        enable_asr=False,
        use_cache=False,
    )

    assert [record.video_id for record in records] == ["video-1"]
