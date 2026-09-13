import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from enrich import (  # noqa: E402
    ARXIV_BATCH_SIZE,
    ARXIV_NUM_RETRIES,
    ARXIV_RETRY_DELAY_SECONDS,
    chunk_ids,
    fetch_arxiv_records,
    has_complete_metadata,
    normalize_arxiv_id,
)


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

    def test_detects_complete_crawler_metadata(self):
        self.assertTrue(
            has_complete_metadata(
                {
                    "title": "A paper",
                    "authors": ["Author"],
                    "summary": "Abstract",
                }
            )
        )
        self.assertFalse(
            has_complete_metadata(
                {"title": "A paper", "authors": [], "summary": "Abstract"}
            )
        )

    def test_fetches_metadata_in_arxiv_id_batches(self):
        ids = [f"2609.{index:05d}" for index in range(101)]
        searches = []
        clients = []

        class FakeClient:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                clients.append(self)

            def results(self, search):
                searches.append(search)
                return [
                    SimpleNamespace(
                        entry_id=f"https://arxiv.org/abs/{paper_id}v1"
                    )
                    for paper_id in search.id_list
                ]

        def fake_search(**kwargs):
            return SimpleNamespace(**kwargs)

        with patch("enrich.arxiv.Client", FakeClient), patch(
            "enrich.arxiv.Search", fake_search
        ):
            records = fetch_arxiv_records(ids)

        self.assertEqual([100, 1], [len(search.id_list) for search in searches])
        self.assertEqual(101, len(records))
        self.assertEqual(
            {
                "page_size": ARXIV_BATCH_SIZE,
                "delay_seconds": ARXIV_RETRY_DELAY_SECONDS,
                "num_retries": ARXIV_NUM_RETRIES,
            },
            clients[0].kwargs,
        )


if __name__ == "__main__":
    unittest.main()
