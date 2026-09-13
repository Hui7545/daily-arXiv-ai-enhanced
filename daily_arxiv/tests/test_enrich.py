import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from enrich import chunk_ids, normalize_arxiv_id  # noqa: E402


class EnrichHelpersTests(unittest.TestCase):
    def test_normalizes_arxiv_id_paths_and_versions(self):
        self.assertEqual("2609.10750", normalize_arxiv_id("2609.10750"))
        self.assertEqual(
            "2609.10750",
            normalize_arxiv_id("https://arxiv.org/abs/2609.10750v1"),
        )

    def test_chunks_ids_at_arxiv_batch_limit(self):
        ids = list(range(250))
        chunks = list(chunk_ids(ids))
        self.assertEqual(3, len(chunks))
        self.assertEqual(100, len(chunks[0]))
        self.assertEqual(50, len(chunks[2]))


if __name__ == "__main__":
    unittest.main()
