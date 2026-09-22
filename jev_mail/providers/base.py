from __future__ import annotations

from typing import Protocol

import httpx


class ProviderError(Exception):
    """Raised when a Jev backend can't be reached or returns something unexpected."""


def describe_http_error(exc: httpx.HTTPError) -> str:
    """A short, human-readable summary -- httpx's own str() on an
    HTTPStatusError includes the full request URL plus an MDN boilerplate
    line ("For more information check: developer.mozilla.org/...") which is
    unreadable dumped into a status line or a single-line CLI error."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"{exc.response.status_code} {exc.response.reason_phrase}"
    return str(exc)


class JevClient(Protocol):
    def decide(self, state: str, categories: dict[str, str]) -> dict[str, float]:
        """Given `state` text and {category_name: description}, returns
        {category_name: probability_it_applies}, one independent yes/no
        judgment per category (multi-label)."""
        ...


def build_noul_questions(categories: dict[str, str]) -> dict:
    """{category: description} -> the `questions` block Jev expects: one
    yes/no (noul) question per category, phrased from its description."""
    return {
        name: {
            "type": "noul",
            "instructions": f"Does this apply: {description}",
            "criteria": {"true": description, "false": "Does not apply"},
        }
        for name, description in categories.items()
    }


def extract_probabilities(answers: dict, categories: list[str]) -> dict[str, float]:
    """Normalizes a decisions-style response's `answers` block back to
    {category: probability}."""
    result: dict[str, float] = {}
    for name in categories:
        answer = answers.get(name)
        if not isinstance(answer, dict):
            raise ProviderError(f"no answer returned for category {name!r}")
        probability = answer.get("noul")
        if probability is None:
            raise ProviderError(f"couldn't find a probability in the answer for {name!r}: {answer!r}")
        result[name] = float(probability)
    return result
