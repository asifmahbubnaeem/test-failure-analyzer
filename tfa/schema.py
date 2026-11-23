"""The verdict every analyzer returns, and the JSON schema the model must follow."""

from dataclasses import asdict, dataclass, field

CATEGORIES = ("product_bug", "test_bug", "flaky", "environment", "infra")

DEFINITIONS = {
    "product_bug": "the application under test behaves wrongly (wrong result, missing validation, wrong data)",
    "test_bug": "the test code or test data is wrong (bad locator, wrong expected value, wrong assertion, bad credentials in test data)",
    "flaky": "the failure is intermittent with no relevant change (timing, random server errors, races); a rerun would likely pass",
    "environment": "something the tests depend on is missing or misconfigured (database down, missing config or env var, service unreachable)",
    "infra": "the CI runner itself failed (job timeout, out of memory, disk full, cannot download dependencies)",
}

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "root_cause": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["category", "confidence", "root_cause", "evidence"],
}


@dataclass
class Verdict:
    category: str
    confidence: float
    root_cause: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class InvalidVerdict(ValueError):
    pass


def validate(data: dict) -> Verdict:
    """Turn the model's JSON into a Verdict, or raise InvalidVerdict saying what is wrong."""
    if not isinstance(data, dict):
        raise InvalidVerdict("answer is not a JSON object")
    category = str(data.get("category", "")).strip().lower()
    if category not in CATEGORIES:
        raise InvalidVerdict(f"category {category!r} is not one of {', '.join(CATEGORIES)}")
    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        raise InvalidVerdict("confidence is not a number") from None
    evidence = data.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = [str(evidence)]
    return Verdict(
        category=category,
        confidence=min(max(confidence, 0.0), 1.0),
        root_cause=str(data.get("root_cause", "")).strip(),
        evidence=[str(e) for e in evidence][:10],
    )
