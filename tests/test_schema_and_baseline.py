import json
import unittest
from pathlib import Path

from tfa import baseline
from tfa.case import load
from tfa.llm import Reply
from tfa.schema import InvalidVerdict, validate

CASES = Path(__file__).parent / "fixtures" / "cases"


class FakeClient:
    """Returns the given answers in order and records what it was sent."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.sent = []

    def chat(self, messages, json_schema=None, think=False):
        self.sent.append(messages)
        return Reply(content=self.answers.pop(0), seconds=1.0, prompt_tokens=100, output_tokens=20)


GOOD = json.dumps({"category": "product_bug", "confidence": 0.8, "root_cause": "x", "evidence": ["y"]})


class SchemaTests(unittest.TestCase):
    def test_valid_answer_is_normalised(self):
        v = validate({"category": " Product_Bug ", "confidence": 1.7, "root_cause": "r", "evidence": "e"})
        self.assertEqual((v.category, v.confidence, v.evidence), ("product_bug", 1.0, ["e"]))

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(InvalidVerdict):
            validate({"category": "bug", "confidence": 0.5})


class BaselineTests(unittest.TestCase):
    def test_label_never_reaches_the_model(self):
        client = FakeClient(GOOD)
        baseline.classify(load(CASES / "case-0001"), client)
        prompt = json.dumps(client.sent[0])
        label = json.loads((CASES / "case-0001" / "label.json").read_text())
        for secret in (label["scenario"], label["root_cause"], label["case_id"]):
            self.assertNotIn(secret, prompt)

    def test_invalid_answer_gets_one_retry(self):
        client = FakeClient('{"category": "nope"}', GOOD)
        verdict, usage = baseline.classify(load(CASES / "case-0001"), client)
        self.assertEqual((verdict.category, usage["attempts"]), ("product_bug", 2))
        self.assertIn("invalid", client.sent[1][-1]["content"])

    def test_two_invalid_answers_raise(self):
        with self.assertRaises(InvalidVerdict):
            baseline.classify(load(CASES / "case-0001"), FakeClient("not json", "still not json"))

    def test_evidence_is_bounded_and_keeps_the_key_lines(self):
        text = baseline.evidence(load(CASES / "case-0024"))
        self.assertLessEqual(len(text), baseline.MAX_EVIDENCE_CHARS + 20)
        self.assertIn("psycopg.OperationalError", text)


if __name__ == "__main__":
    unittest.main()
