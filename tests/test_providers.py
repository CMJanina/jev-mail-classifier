import httpx
import pytest

from jev_mail.config import JevSettings
from jev_mail.providers import ProviderError, get_jev_client
from jev_mail.providers.base import describe_http_error


def _fake_response(json_body: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=json_body, request=httpx.Request("POST", "https://example.com"))


CATEGORIES = {"invoice": "Invoice or billing", "urgent": "Time-sensitive"}


@pytest.mark.parametrize(
    "provider,url,model,label",
    [
        ("openrouter", "https://openrouter.ai/api/alpha/decisions", "typesafe/jev-1.13", "OpenRouter"),
        ("typesafe", "https://api.typesafe.ai/v1/systemone", "jev-latest", "TypeSafe API"),
    ],
)
def test_decide_normalizes_probabilities(monkeypatch, provider, url, model, label):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _fake_response(
            {
                "answers": {
                    "invoice": {"type": "noul", "noul": 0.9},
                    "urgent": {"type": "noul", "noul": 0.2},
                }
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    client = get_jev_client(JevSettings(provider=provider, **{f"{provider}_api_key": "test-key"}))
    result = client.decide("some email body", CATEGORIES)

    assert captured["url"] == url
    assert captured["json"]["model"] == model
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["timeout"] == 15.0
    assert result == {"invoice": 0.9, "urgent": 0.2}
    assert captured["json"]["state"] == "some email body"
    assert set(captured["json"]["questions"]) == set(CATEGORIES)

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _fake_response({}, status_code=403))
    with pytest.raises(ProviderError, match=f"{label} request failed: 403 Forbidden"):
        client.decide("body", CATEGORIES)


def test_decide_raises_provider_error_on_http_failure(monkeypatch):
    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", fake_post)
    client = get_jev_client(JevSettings(provider="openrouter", openrouter_api_key="test-key"))

    with pytest.raises(ProviderError):
        client.decide("body", CATEGORIES)


def test_describe_http_error_status_error_is_short():
    response = _fake_response({}, status_code=403)
    exc = httpx.HTTPStatusError("403 Forbidden for url ...", request=response.request, response=response)
    assert describe_http_error(exc) == "403 Forbidden"


def test_describe_http_error_non_status_error_passes_through():
    exc = httpx.ConnectError("Connection refused")
    assert describe_http_error(exc) == "Connection refused"


def test_decide_error_message_is_short_not_the_full_httpx_dump(monkeypatch):
    """Regression: httpx's own str() on an HTTPStatusError includes the full
    request URL plus an MDN boilerplate line -- unreadable dumped into a
    single status line in the TUI or CLI stderr."""
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _fake_response({}, status_code=403))
    client = get_jev_client(JevSettings(provider="openrouter", openrouter_api_key="test-key"))

    with pytest.raises(ProviderError) as exc_info:
        client.decide("body", CATEGORIES)

    message = str(exc_info.value)
    assert "403" in message
    assert "developer.mozilla.org" not in message
    assert len(message) < 100


def test_decide_raises_provider_error_on_missing_answer(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _fake_response({"answers": {}}))
    client = get_jev_client(JevSettings(provider="openrouter", openrouter_api_key="test-key"))

    with pytest.raises(ProviderError):
        client.decide("body", CATEGORIES)


def test_get_jev_client_auto_detect_priority(monkeypatch):
    captured = []

    def fake_post(url, **kwargs):
        captured.append((url, kwargs["headers"]["Authorization"]))
        return _fake_response({"answers": {}})

    monkeypatch.setattr(httpx, "post", fake_post)
    env = {"openrouter_api_key": "or-key"}
    client = get_jev_client(JevSettings(provider="auto", **env))
    client.decide("body", {})
    assert captured[-1] == ("https://openrouter.ai/api/alpha/decisions", "Bearer or-key")

    env = {"typesafe_api_key": "ts-key", "openrouter_api_key": "or-key"}
    client = get_jev_client(JevSettings(provider="auto", **env))
    client.decide("body", {})
    assert captured[-1] == ("https://api.typesafe.ai/v1/systemone", "Bearer ts-key")


def test_get_jev_client_auto_detect_no_keys_raises():
    with pytest.raises(ProviderError):
        get_jev_client(JevSettings(provider="auto"))


def test_get_jev_client_explicit_provider_missing_key_raises():
    with pytest.raises(ProviderError):
        get_jev_client(JevSettings(provider="openrouter"))


def test_get_jev_client_explicit_provider_unknown_raises():
    with pytest.raises(ProviderError):
        get_jev_client(JevSettings(provider="not-a-real-provider", typesafe_api_key="x"))


def test_provider_ignores_environment_keys(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "environment-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "environment-key")
    with pytest.raises(ProviderError, match="no Jev API key"):
        get_jev_client(JevSettings())
