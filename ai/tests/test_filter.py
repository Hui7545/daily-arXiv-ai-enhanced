import os
import sys
import unittest
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filter import keep, priority, load_items  # noqa: E402


def make_item(**ai_overrides):
    ai = {
        "tldr": "t",
        "motivation": "m",
        "method": "m",
        "result": "r",
        "conclusion": "c",
        "is_recommendation_related": True,
        "is_high_quality": True,
        "is_known_affiliation": False,
        "priority_score": 50,
        "reason": "ok",
    }
    ai.update(ai_overrides)
    return {"id": "x", "title": "t", "AI": ai}


class KeepTests(unittest.TestCase):
    def test_keeps_recommendation_related_high_quality(self):
        self.assertTrue(keep(make_item(priority_score=80)))

    def test_drops_not_recommendation_related(self):
        self.assertFalse(keep(make_item(is_recommendation_related=False)))

    def test_low_quality_does_not_exclude_relevant_paper(self):
        # is_high_quality is intentionally NOT a hard gate; only relevance decides.
        self.assertTrue(keep(make_item(is_high_quality=False, priority_score=30)))

    def test_missing_judgment_fields_are_dropped(self):
        # is_recommendation_related defaults to False when absent
        item = {"id": "x", "title": "t", "AI": {"tldr": "t"}}
        self.assertFalse(keep(item))

    def test_missing_Ai_object_behaves_like_not_relevant(self):
        self.assertFalse(keep({"id": "x", "title": "t"}))


class PriorityTests(unittest.TestCase):
    def test_priority_from_score(self):
        self.assertEqual(priority(make_item(priority_score=80)), 80.0)

    def test_priority_default_when_missing(self):
        self.assertEqual(priority({"id": "x", "title": "t"}), 0.0)

    def test_priority_default_on_bad_value(self):
        item = {"id": "x", "title": "t", "AI": {"priority_score": "abc"}}
        self.assertEqual(priority(item), 0.0)


class LoadItemsTests(unittest.TestCase):
    def test_load_items_skips_blank_lines(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            f.write(json.dumps({"id": "1"}) + "\n\n" + json.dumps({"id": "2"}) + "\n")
            path = f.name
        try:
            items = load_items(path)
            self.assertEqual([i["id"] for i in items], ["1", "2"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
