from __future__ import annotations

from typing import Protocol


class ProviderError(Exception):
    """Raised when a Jev backend can't be reached or returns something unexpected."""


class JevClient(Protocol):
    def decide(self, state: str, categories: dict[str, str]) -> dict[str, float]:
        """Given `state` text and {category_name: description}, returns
        {category_name: probability_it_applies}, one independent yes/no
        judgment per category (multi-label)."""
        ...


def build_noul_questions(categories: dict[str, str], noul_type: str = "noul") -> dict:
    """{category: description} -> the `questions` block Jev expects: one
    yes/no (noul) question per category, phrased from its description."""
    return {
        name: {
            "type": noul_type,
            "instructions": f"Does this apply: {description}",
            "criteria": {"true": description, "false": "Does not apply"},
        }
        for name, description in categories.items()
    }


def extract_probabilities(answers: dict, categories: list[str]) -> dict[str, float]:
    """Normalizes a decisions-style response's `answers` block back to
    {category: probability}, tolerant of the noul/boolean naming difference
    between backends."""
    result: dict[str, float] = {}
    for name in categories:
        answer = answers.get(name)
        if not isinstance(answer, dict):
            raise ProviderError(f"no answer returned for category {name!r}")
        probability = answer.get("noul", answer.get("boolean"))
        if probability is None:
            raise ProviderError(f"couldn't find a probability in the answer for {name!r}: {answer!r}")
        result[name] = float(probability)
    return result
