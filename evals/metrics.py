"""Scores for a list of (expected, predicted) pairs."""

from collections import Counter, defaultdict

from tfa.schema import CATEGORIES

ERROR = "(no answer)"


def accuracy(pairs: list[tuple[str, str]]) -> float:
    return sum(e == p for e, p in pairs) / len(pairs) if pairs else 0.0


def scenario_weighted_accuracy(rows: list[dict]) -> float:
    """Each scenario counts once: repeats of an identical failure don't inflate the score."""
    by_scenario = defaultdict(list)
    for r in rows:
        by_scenario[r["scenario"]].append(r["expected"] == r["predicted"])
    return sum(sum(v) / len(v) for v in by_scenario.values()) / len(by_scenario) if by_scenario else 0.0


def per_category(pairs: list[tuple[str, str]]) -> dict[str, dict]:
    """Precision, recall and support per category."""
    out = {}
    for c in CATEGORIES:
        tp = sum(e == c and p == c for e, p in pairs)
        predicted = sum(p == c for _, p in pairs)
        actual = sum(e == c for e, _ in pairs)
        if actual or predicted:
            out[c] = {
                "support": actual,
                "precision": tp / predicted if predicted else 0.0,
                "recall": tp / actual if actual else 0.0,
            }
    return out


def confusion(pairs: list[tuple[str, str]]) -> dict[str, Counter]:
    m = defaultdict(Counter)
    for e, p in pairs:
        m[e][p] += 1
    return m


def confusion_table(pairs: list[tuple[str, str]]) -> str:
    """Markdown table: rows are the true category, columns what was predicted."""
    m = confusion(pairs)
    rows = [c for c in CATEGORIES if c in m]
    cols = [c for c in CATEGORIES if any(m[r][c] for r in rows)]
    if any(m[r][ERROR] for r in rows):
        cols.append(ERROR)
    head = "| true \\ predicted | " + " | ".join(cols) + " |"
    sep = "| --- |" + " --- |" * len(cols)
    body = [f"| {r} | " + " | ".join(str(m[r][c] or "") for c in cols) + " |" for r in rows]
    return "\n".join([head, sep, *body])
