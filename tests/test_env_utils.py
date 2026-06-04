from src.env_utils import is_real_env_value, normalize_env_value


def test_normalize_env_value_strips_whitespace_and_quotes():
    assert normalize_env_value(" 'your_key' ") == "your_key"
    assert normalize_env_value(' "real-key" ') == "real-key"


def test_is_real_env_value_rejects_empty_and_placeholder_values():
    assert is_real_env_value(None) is False
    assert is_real_env_value("   ") is False
    assert is_real_env_value('"your_openai_compatible_api_key"') is False
    assert is_real_env_value("'replace_me'") is False
    assert is_real_env_value("YOUR_YOUTUBE_API_KEY") is False
    assert is_real_env_value("REPLACE_ME") is False
    assert is_real_env_value("填入真实密钥") is False


def test_is_real_env_value_accepts_non_placeholder_values():
    assert is_real_env_value("sk-test-value") is True
