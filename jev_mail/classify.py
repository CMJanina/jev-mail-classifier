from __future__ import annotations

from jev_mail.config import AppConfig, Category
from jev_mail.providers.base import JevClient


def classify(client: JevClient, config: AppConfig, state: str) -> dict[str, float]:
    """One Jev call, one noul question per configured category."""
    categories = {c.name: c.description for c in config.categories}
    return client.decide(state, categories)


def matched_categories(config: AppConfig, probabilities: dict[str, float]) -> list[Category]:
    """Categories whose probability clears their threshold (per-category
    override, else jev.default_threshold)."""
    by_name = {c.name: c for c in config.categories}
    return [
        by_name[name]
        for name, probability in probabilities.items()
        if probability >= config.category_threshold(by_name[name])
    ]
