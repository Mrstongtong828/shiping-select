from src.schema import SubtitlePayload
from src.search_youtube import _build_records_from_responses, _fetch_transcript


def test_build_records_from_youtube_api_responses():
    search_items = [
        {
            "id": {"videoId": "abc123"},
            "snippet": {
                "title": "PCA tutorial",
                "channelTitle": "Course Channel",
                "description": "Intro to PCA",
                "publishedAt": "2026-01-01T00:00:00Z",
            },
        }
    ]
    detail_items = [
        {
            "id": "abc123",
            "snippet": {
                "title": "PCA tutorial full",
                "channelTitle": "Course Channel",
                "description": "Full PCA lesson",
                "publishedAt": "2026-01-02T00:00:00Z",
            },
            "statistics": {"viewCount": "1234", "likeCount": "56"},
            "contentDetails": {"duration": "PT1H2M3S"},
        }
    ]

    records = _build_records_from_responses(
        search_items,
        detail_items,
        subtitle_limit=6000,
        fetch_transcript=lambda video_id, limit: SubtitlePayload(
            text=f"subtitle for {video_id}",
            language="en",
            source="youtube_transcript",
        ),
    )

    assert len(records) == 1
    record = records[0]
    assert record.platform == "youtube"
    assert record.video_id == "abc123"
    assert record.title == "PCA tutorial full"
    assert record.url == "https://www.youtube.com/watch?v=abc123"
    assert record.author == "Course Channel"
    assert record.view == 1234
    assert record.like == 56
    assert record.duration == 3723
    assert record.has_subtitle is True
    assert record.subtitle_text == "subtitle for abc123"


def test_fetch_transcript_uses_current_youtube_transcript_api(monkeypatch):
    class FakeLine:
        def __init__(self, text: str):
            self.text = text

    class FakeTranscript:
        language_code = "en"

        def __iter__(self):
            return iter([FakeLine("hello"), FakeLine("world")])

    class FakeYouTubeTranscriptApi:
        def fetch(self, video_id, languages):
            assert video_id == "abc123"
            assert languages == ["zh-Hans", "zh-CN", "zh", "en"]
            return FakeTranscript()

    monkeypatch.setattr("src.search_youtube.YouTubeTranscriptApi", FakeYouTubeTranscriptApi)

    subtitle = _fetch_transcript("abc123", 6000)

    assert subtitle.text == "hello\nworld"
    assert subtitle.language == "en"
    assert subtitle.source == "youtube_transcript"
