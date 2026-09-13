import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError  # noqa: E402

from structure import Structure  # noqa: E402


def valid_structure(**overrides):
    data = {
        "tldr": "t",
        "motivation": "m",
        "method": "m",
        "result": "r",
        "conclusion": "c",
        "is_relevant": True,
        "is_high_quality": True,
        "is_known_affiliation": True,
        "priority_score": 60,
        "reason": "solid work from a known lab",
    }
    data.update(overrides)
    return Structure(**data)


class StructureJudgmentFieldsTests(unittest.TestCase):
    def test_accepts_all_judgment_fields(self):
        s = valid_structure()
        self.assertTrue(s.is_relevant)
        self.assertTrue(s.is_high_quality)
        self.assertTrue(s.is_known_affiliation)
        self.assertEqual(s.priority_score, 60)
        self.assertEqual(s.reason, "solid work from a known lab")

    def test_priority_score_respects_upper_bound(self):
        with self.assertRaises(ValidationError):
            valid_structure(priority_score=101)

    def test_priority_score_respects_lower_bound(self):
        with self.assertRaises(ValidationError):
            valid_structure(priority_score=-1)

    def test_priority_score_zero_is_valid(self):
        s = valid_structure(priority_score=0)
        self.assertEqual(s.priority_score, 0)

    def test_missing_judgment_field_degrades_to_default(self):
        # Judgment fields have safe defaults so a model that omits one (e.g. DeepSeek
        # occasionally dropping is_known_affiliation) does not fail the whole batch;
        # the paper is then treated as non-relevant and filtered out downstream.
        data = {
            "tldr": "t",
            "motivation": "m",
            "method": "m",
            "result": "r",
            "conclusion": "c",
        }
        s = Structure(**data)
        self.assertFalse(s.is_relevant)
        self.assertFalse(s.is_known_affiliation)
        self.assertEqual(s.priority_score, 0)
        self.assertEqual(s.reason, "")

    def test_model_dump_includes_new_fields(self):
        s = valid_structure()
        dumped = s.model_dump()
        for field in (
            "is_relevant",
            "is_high_quality",
            "is_known_affiliation",
            "priority_score",
            "reason",
        ):
            self.assertIn(field, dumped)

    def test_false_text_field_is_coerced_to_string(self):
        s = Structure(**{**valid_structure().__dict__, "method": False})
        self.assertEqual("false", s.method)

    def test_missing_text_fields_use_safe_defaults(self):
        s = Structure(
            is_relevant=True,
            is_high_quality=True,
            is_known_affiliation=False,
            priority_score=50,
            reason="ok",
        )
        self.assertEqual("Summary generation failed", s.tldr)
        self.assertEqual("Method extraction failed", s.method)

    def test_string_boolean_field_is_normalized(self):
        s = Structure(
            **{**valid_structure().__dict__, "is_relevant": "False"}
        )
        self.assertFalse(s.is_relevant)


if __name__ == "__main__":
    unittest.main()
