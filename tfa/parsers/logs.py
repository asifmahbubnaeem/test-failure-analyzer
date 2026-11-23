"""Shrink logs to the lines that carry evidence. A small local model reads slowly, and a
600-line log of repeated stack frames hides the one line that matters."""

import re
from collections import Counter

# Final line of a Python traceback, e.g. "KeyError: 'TAX_RATE'" or "psycopg.OperationalError: ..."
EXCEPTION_LINE = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt))(?::\s?(.*))?$")
# uvicorn access line: INFO:     127.0.0.1:41968 - "POST /api/cart/desk-lamp HTTP/1.1" 500 Internal Server Error
ACCESS_LINE = re.compile(r'"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) (\S+) HTTP/[\d.]+" (\d{3})')


def exception_summary(log: str, limit: int = 8) -> list[str]:
    """Distinct exception lines with counts, most frequent first."""
    counts = Counter()
    for line in log.splitlines():
        m = EXCEPTION_LINE.match(line.strip())
        if m:
            counts[line.strip()[:240]] += 1
    return [f"{n}x {text}" for text, n in counts.most_common(limit)]


def status_summary(log: str) -> dict[str, int]:
    """Count of HTTP responses by status code, from access-log lines."""
    counts = Counter(m.group(3) for m in ACCESS_LINE.finditer(log))
    return dict(sorted(counts.items()))


def failing_requests(log: str, limit: int = 10) -> list[str]:
    """Distinct method + path pairs that got a 5xx, with counts."""
    counts = Counter()
    for m in ACCESS_LINE.finditer(log):
        if m.group(3).startswith("5"):
            counts[f"{m.group(1)} {m.group(2)} -> {m.group(3)}"] += 1
    return [f"{n}x {text}" for text, n in counts.most_common(limit)]


def error_lines(test_log: str, limit: int = 60) -> list[str]:
    """pytest's 'E ' assertion lines and the FAILED summary lines, without repeats."""
    seen, out = set(), []
    for line in test_log.splitlines():
        s = line.rstrip()
        if s.startswith("E ") or s.startswith("FAILED ") or re.match(r"^=+ .*(failed|passed|error).* =+$", s):
            key = s.strip()
            if key not in seen:
                seen.add(key)
                out.append(s[:300])
    return out[:limit]
