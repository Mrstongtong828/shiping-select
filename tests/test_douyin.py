import json

import pytest

from src.search_douyin import build_douyin_records_from_payload, search_douyin_videos


def test_build_douyin_records_from_reference_payload():
    payload = {
        "搜索关键词": "PCA 主成分分析",
        "视频列表": [
            {
                "标题": "PCA 短视频讲解",
                "官网链接": "https://www.douyin.com/video/123",
                "点赞数": "1.2万",
            }
        ],
    }

    records = build_douyin_records_from_payload(payload, limit=5)

    assert len(records) == 1
    assert records[0].platform == "douyin"
    assert records[0].title == "PCA 短视频讲解"
    assert records[0].url == "https://www.douyin.com/video/123"
    assert records[0].like == 12000
    assert records[0].has_subtitle is False


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls = []
    response = None
    error = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json=None, headers=None):
        self.__class__.calls.append({"url": url, "json": json, "headers": headers})
        if self.__class__.error:
            raise self.__class__.error
        return self.__class__.response


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = None
    FakeAsyncClient.error = None
    monkeypatch.setattr("src.search_douyin.httpx.AsyncClient", FakeAsyncClient)


@pytest.mark.asyncio
async def test_search_douyin_videos_uses_external_video_search_api(monkeypatch):
    monkeypatch.setenv("DOUYIN_SEARCH_MODE", "external_api")
    monkeypatch.setenv("DOUYIN_EXTERNAL_API_BASE", "http://127.0.0.1:5555")
    monkeypatch.setenv("DOUYIN_EXTERNAL_API_TOKEN", "secret-token")
    FakeAsyncClient.response = FakeResponse(
        {
            "data": [
                {
                    "aweme_id": "726",
                    "desc": "PCA 视频讲解",
                    "share_url": "https://www.douyin.com/video/726",
                    "author": {"nickname": "张老师"},
                    "statistics": {"digg_count": 321},
                    "create_time": 1710000000,
                }
            ]
        }
    )

    records = await search_douyin_videos("PCA", limit=5)

    assert len(records) == 1
    assert records[0].platform == "douyin"
    assert records[0].video_id == "726"
    assert records[0].title == "PCA 视频讲解"
    assert records[0].url == "https://www.douyin.com/video/726"
    assert records[0].author == "张老师"
    assert records[0].like == 321
    assert FakeAsyncClient.calls[0]["url"] == "http://127.0.0.1:5555/douyin/search/video"
    assert FakeAsyncClient.calls[0]["json"]["keyword"] == "PCA"
    assert FakeAsyncClient.calls[0]["headers"]["token"] == "secret-token"


@pytest.mark.asyncio
async def test_search_douyin_videos_falls_back_to_reference_json_when_external_api_fails(monkeypatch, tmp_path):
    sample = tmp_path / "douyin.json"
    sample.write_text(
        json.dumps(
            {
                "videos": [
                    {
                        "title": "fallback video",
                        "url": "https://www.douyin.com/video/fallback",
                        "digg_count": 8,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DOUYIN_SEARCH_MODE", "external_api")
    monkeypatch.setenv("DOUYIN_EXTERNAL_API_BASE", "http://127.0.0.1:5555")
    monkeypatch.setenv("DOUYIN_SAMPLE_JSON", str(sample))
    FakeAsyncClient.error = RuntimeError("service down")

    records = await search_douyin_videos("PCA", limit=5)

    assert len(records) == 1
    assert records[0].title == "fallback video"
    assert records[0].url == "https://www.douyin.com/video/fallback"


@pytest.mark.asyncio
async def test_search_douyin_videos_falls_back_to_reference_json_when_external_api_returns_empty(monkeypatch, tmp_path):
    sample = tmp_path / "douyin.json"
    sample.write_text(
        json.dumps({"items": [{"title": "sample item", "url": "https://www.douyin.com/video/sample"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DOUYIN_SEARCH_MODE", "external_api")
    monkeypatch.setenv("DOUYIN_EXTERNAL_API_BASE", "http://127.0.0.1:5555")
    monkeypatch.setenv("DOUYIN_SAMPLE_JSON", str(sample))
    FakeAsyncClient.response = FakeResponse({"data": []})

    records = await search_douyin_videos("PCA", limit=5)

    assert len(records) == 1
    assert records[0].title == "sample item"
