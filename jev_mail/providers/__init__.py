from __future__ import annotations

import os

from jev_mail.config import JevSettings

from .base import DecisionsClient, JevClient, ProviderError

# (provider name, env var, URL, model, error label), in auto-detect priority order.
_BACKENDS = (
    ("typesafe", "TYPESAFE_API_KEY", "https://api.typesafe.ai/v1/systemone", "jev-latest", "TypeSafe API"),
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/alpha/decisions", "typesafe/jev-1.13", "OpenRouter"),
)

__all__ = ["JevClient", "ProviderError", "get_jev_client"]


def get_jev_client(settings: JevSettings, env: dict | None = None) -> JevClient:
    env = env if env is not None else os.environ

    if settings.provider == "auto":
        for _, env_var, url, model, label in _BACKENDS:
            api_key = env.get(env_var)
            if api_key:
                return DecisionsClient(api_key, url, model, label)
        raise ProviderError(
            "no Jev API key found -- set TYPESAFE_API_KEY or OPENROUTER_API_KEY "
            "(run `jev-mail configure` to set one)"
        )

    for name, env_var, url, model, label in _BACKENDS:
        if settings.provider == name:
            api_key = env.get(env_var)
            if not api_key:
                raise ProviderError(f"jev.provider is {name!r} but {env_var} isn't set")
            return DecisionsClient(api_key, url, model, label)

    raise ProviderError(f"unknown jev.provider: {settings.provider!r}")
