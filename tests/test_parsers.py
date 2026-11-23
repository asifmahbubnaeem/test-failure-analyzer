import unittest
from pathlib import Path

from tfa.case import load
from tfa.parsers import junit, logs

CASES = Path(__file__).parent / "fixtures" / "cases"


class JunitTests(unittest.TestCase):
    def test_counts_and_failure_from_real_report(self):
        r = load(CASES / "case-0001").report
        self.assertEqual((r.tests, len(r.failures), r.skipped, r.passed), (21, 1, 0, 20))
        f = r.failures[0]
        self.assertIn("test_order_summary_totals_are_correct", f.test)
        self.assertEqual(f.kind, "failure")
        self.assertIn("Total mismatch", f.message)

    def test_failure_element_without_children_is_still_found(self):
        # An ElementTree element with no children is falsy; the parser must not skip it.
        xml = '<testsuite><testcase classname="a" name="t"><failure message="boom"/></testcase></testsuite>'
        self.assertEqual(junit.parse(xml).failures[0].message, "boom")

    def test_testsuites_wrapper_skips_and_errors(self):
        xml = (
            "<testsuites><testsuite>"
            '<testcase classname="a" name="ok"/>'
            '<testcase classname="a" name="skip"><skipped/></testcase>'
            '<testcase classname="a" name="err"><error message="setup">trace</error></testcase>'
            "</testsuite></testsuites>"
        )
        r = junit.parse(xml)
        self.assertEqual((r.tests, r.skipped, r.passed), (3, 1, 1))
        self.assertEqual((r.failures[0].kind, r.failures[0].details), ("error", "trace"))


class LogTests(unittest.TestCase):
    def test_exception_and_status_summaries(self):
        app = load(CASES / "case-0022").app_log
        self.assertEqual(logs.exception_summary(app), ["3x KeyError: 'TAX_RATE'"])
        self.assertEqual(logs.status_summary(app)["500"], 3)
        self.assertEqual(logs.failing_requests(app), ["3x GET /checkout-step-two.html -> 500"])

    def test_database_errors_are_counted_once(self):
        app = load(CASES / "case-0024").app_log
        top = logs.exception_summary(app)[0]
        self.assertTrue(top.startswith("15x psycopg.OperationalError"), top)

    def test_error_lines_keep_assertions_and_summary_without_repeats(self):
        lines = logs.error_lines(load(CASES / "case-0001").test_log)
        self.assertTrue(any(line.startswith("E ") and "Total mismatch" in line for line in lines))
        self.assertTrue(any("1 failed, 20 passed" in line for line in lines))
        self.assertEqual(len(lines), len(set(line.strip() for line in lines)))


if __name__ == "__main__":
    unittest.main()
