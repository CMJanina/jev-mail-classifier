from __future__ import annotations

from jev_mail.config import JevSettings

from .base import DecisionsClient, JevClient, ProviderError

# (provider name, settings field, URL, model, error label), in auto-detect priority order.
_BACKENDS = (
    ("typesafe", "typesafe_api_key", "https://api.typesafe.ai/v1/systemone", "jev-latest", "TypeSafe API"),
    ("openrouter", "openrouter_api_key", "https://openrouter.ai/api/alpha/decisions", "typesafe/jev-1.13", "OpenRouter"),
)

__all__ = ["JevClient", "ProviderError", "get_jev_client"]


def get_jev_client(settings: JevSettings) -> JevClient:
    if settings.provider == "auto":
        for _, key_field, url, model, label in _BACKENDS:
            api_key = getattr(settings, key_field)
            if api_key:
                return DecisionsClient(api_key, url, model, label)
        raise ProviderError(
            "no Jev API key found -- set jev.typesafe_api_key or jev.openrouter_api_key in config.yaml "
            "(run `jev-mail configure` to set one)"
        )

    for name, key_field, url, model, label in _BACKENDS:
        if settings.provider == name:
            api_key = getattr(settings, key_field)
            if not api_key:
                raise ProviderError(f"jev.provider is {name!r} but {key_field} isn't set")
            return DecisionsClient(api_key, url, model, label)

    raise ProviderError(f"unknown jev.provider: {settings.provider!r}")
