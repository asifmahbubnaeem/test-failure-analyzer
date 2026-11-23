"""A case is one failed CI run: the files the agent may read. The label lives next to it but is
never loaded here, so nothing that reaches a model can contain the answer."""

from dataclasses import dataclass
from pathlib import Path

from tfa.parsers import junit


@dataclass
class Case:
    case_id: str
    report: junit.Report
    test_log: str
    app_log: str


def load(path: Path) -> Case:
    path = Path(path)
    read = lambda name: (path / name).read_text(errors="replace") if (path / name).exists() else ""  # noqa: E731
    return Case(
        case_id=path.name,
        report=junit.parse(read("junit.xml")),
        test_log=read("test_log.txt"),
        app_log=read("shop.log"),
    )
