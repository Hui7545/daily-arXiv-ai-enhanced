import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from daily_arxiv.pipelines import (  # noqa: E402
    DailyArxivPipeline,
    extract_author_affiliations,
    normalize_title,
)


class ExtractAuthorAffiliationsTests(unittest.TestCase):
    def test_extracts_institutions_countries_and_raw_affiliations(self):
        work = {
            "authorships": [
                {
                    "author": {"display_name": "Alice"},
                    "institutions": [
                        {
                            "display_name": "Tsinghua University",
                            "country_code": "CN",
                        }
                    ],
                    "raw_affiliation_strings": ["Tsinghua University, Beijing"],
                },
                {
                    "author": {"display_name": "Bob"},
                    "institutions": [
                        {
                            "display_name": "Google Research",
                            "country_code": "US",
                        }
                    ],
                    "raw_affiliation_strings": ["Google Research"],
                },
            ]
        }

        affiliations = extract_author_affiliations(work)

        self.assertEqual("Alice", affiliations[0]["author"])
        self.assertEqual(
            ["Tsinghua University"], affiliations[0]["institutions"]
        )
        self.assertEqual(["CN"], affiliations[0]["countries"])
        self.assertEqual(
            ["Tsinghua University, Beijing"],
            affiliations[0]["raw_affiliations"],
        )
        self.assertEqual("Bob", affiliations[1]["author"])

    def test_handles_missing_openalex_data(self):
        self.assertEqual([], extract_author_affiliations(None))
        self.assertEqual([], extract_author_affiliations({}))

    def test_deduplicates_affiliations(self):
        work = {
            "authorships": [
                {
                    "author": {"display_name": "Alice"},
                    "institutions": [
                        {"display_name": "Example Lab", "country_code": "US"},
                        {"display_name": "Example Lab", "country_code": "US"},
                    ],
                }
            ]
        }

        affiliations = extract_author_affiliations(work)

        self.assertEqual(["Example Lab"], affiliations[0]["institutions"])
        self.assertEqual(["US"], affiliations[0]["countries"])


class OpenAlexLookupTests(unittest.TestCase):
    def test_falls_back_to_exact_title_match_when_doi_is_missing(self):
        pipeline = DailyArxivPipeline()
        pipeline.session = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = [
            {"results": []},
            {
                "results": [
                    {"id": "W1", "title": "Attention Is All You Need"},
                    {"id": "W2", "title": "A Different Paper"},
                ]
            },
        ]
        pipeline.session.get.return_value = response
        spider = Mock()

        result = pipeline.fetch_openalex_work(
            "1706.03762",
            "Attention is all you need",
            spider,
        )

        self.assertEqual("W1", result["id"])
        first_params = pipeline.session.get.call_args_list[0].kwargs["params"]
        second_params = pipeline.session.get.call_args_list[1].kwargs["params"]
        self.assertEqual(
            "doi:10.48550/arxiv.1706.03762",
            first_params["filter"],
        )
        self.assertEqual(
            "title.search:Attention is all you need",
            second_params["filter"],
        )

    def test_normalize_title_ignores_case_and_punctuation(self):
        self.assertEqual(
            "attention is all you need",
            normalize_title("Attention: Is All You Need?"),
        )


if __name__ == "__main__":
    unittest.main()
