from src import cache_utils


def test_json_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_utils, "CACHE_DIR", tmp_path / "cache")
    key = cache_utils.build_cache_key("topic", "bilibili", 10)

    cache_utils.save_json_cache("searches", key, {"records": [1, 2, 3]})

    assert cache_utils.load_json_cache("searches", key) == {"records": [1, 2, 3]}
