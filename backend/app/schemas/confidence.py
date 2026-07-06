from typing import Literal

ConfidenceLevel = Literal["low", "medium", "high"]


def normalize_confidence(value: object) -> ConfidenceLevel:
    if isinstance(value, str):
        normalized = value.lower().strip()
        if normalized in {"low", "medium", "high"}:
            return normalized  # type: ignore[return-value]

    return "low"
