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


class DecisionsClient:
    """Client for backends using the Jev decisions request and response format."""

    def __init__(self, api_key: str, url: str, model: str, label: str, timeout: float = 15.0):
        self._url = url
        self._label = label
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def decide(self, state: str, categories: dict[str, str]) -> dict[str, float]:
        questions = build_noul_questions(categories)
        try:
            response = httpx.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"model": self._model, "state": state, "questions": questions},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self._label} request failed: {describe_http_error(exc)}") from exc

        return extract_probabilities(response.json().get("answers", {}), list(categories))
