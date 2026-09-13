import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from scrapy.http import HtmlResponse  # noqa: E402

from daily_arxiv.spiders.arxiv import ArxivSpider  # noqa: E402


class ArxivSpiderTests(unittest.TestCase):
    def test_parses_list_page_metadata(self):
        html = """
        <html>
          <body>
            <div id="dlpage">
              <ul>
                <li><a href="#item1">1</a></li>
                <li><a href="#item2">2</a></li>
              </ul>
            </div>
            <dl>
              <dt>
                <a name="item1"></a>
                <a title="Abstract" href="/abs/2609.12345">Abstract</a>
              </dt>
              <dd>
                <div class="list-title mathjax">
                  <span class="descriptor">Title:</span>
                  Search Ranking with Feedback
                </div>
                <div class="list-authors">
                  <a>Alice Example</a>, <a>Bob Example</a>
                </div>
                <div class="list-comments mathjax">
                  <span class="descriptor">Comments:</span>
                  Accepted at a conference
                </div>
                <div class="list-subjects">
                  <span class="descriptor">Subjects:</span>
                  <span class="primary-subject">
                    Information Retrieval (cs.IR)
                  </span>
                  ; Machine Learning (cs.LG)
                </div>
                <p class="mathjax">
                  A ranking model trained from user feedback.
                </p>
              </dd>
            </dl>
          </body>
        </html>
        """
        response = HtmlResponse(
            url="https://arxiv.org/list/cs.IR/new",
            body=html.encode("utf-8"),
            encoding="utf-8",
        )

        with patch.dict(
            os.environ,
            {"CATEGORIES": "cs.IR", "ARXIV_MAX_PAPERS": "1"},
        ):
            items = list(ArxivSpider().parse(response))

        self.assertEqual(1, len(items))
        self.assertEqual(
            {
                "id": "2609.12345",
                "categories": ["cs.IR", "cs.LG"],
                "pdf": "https://arxiv.org/pdf/2609.12345",
                "abs": "https://arxiv.org/abs/2609.12345",
                "authors": ["Alice Example", "Bob Example"],
                "title": "Search Ranking with Feedback",
                "comment": "Accepted at a conference",
                "summary": "A ranking model trained from user feedback.",
            },
            items[0],
        )


if __name__ == "__main__":
    unittest.main()
