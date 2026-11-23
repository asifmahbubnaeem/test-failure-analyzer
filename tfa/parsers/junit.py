"""Read JUnit XML, the report format most test runners can write (pytest: --junitxml)."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class Failure:
    test: str  # "classname::name"
    kind: str  # "failure" (assertion) or "error" (crash in setup or test)
    message: str
    details: str  # the traceback text the runner recorded


@dataclass
class Report:
    tests: int = 0
    skipped: int = 0
    failures: list[Failure] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return self.tests - self.skipped - len(self.failures)


def parse(xml_text: str) -> Report:
    root = ET.fromstring(xml_text)
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    report = Report()
    for suite in suites:
        for tc in suite.iter("testcase"):
            report.tests += 1
            if tc.find("skipped") is not None:
                report.skipped += 1
                continue
            for kind in ("failure", "error"):
                el = tc.find(kind)
                if el is not None:  # an Element with no children is falsy, so compare to None
                    report.failures.append(
                        Failure(
                            test=f"{tc.get('classname', '')}::{tc.get('name', '')}",
                            kind=kind,
                            message=(el.get("message") or "").strip(),
                            details=(el.text or "").strip(),
                        )
                    )
                    break
    return report
