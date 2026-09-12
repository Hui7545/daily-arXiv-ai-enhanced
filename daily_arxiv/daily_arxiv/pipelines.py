# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import os
import re

import arxiv
import requests


OPENALEX_API_URL = "https://api.openalex.org/works"
OPENALEX_TIMEOUT_SECONDS = 10


def unique_strings(values):
    """Return non-empty strings in their original order without duplicates."""
    result = []
    seen = set()
    for value in values or []:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def normalize_title(title):
    """Normalize a title for an exact comparison between metadata sources."""
    return " ".join(re.sub(r"[^\w]+", " ", (title or "").casefold()).split())


def extract_author_affiliations(work):
    """Convert an OpenAlex work into per-author affiliation records."""
    if not work:
        return []

    records = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        author_name = author.get("display_name")
        institutions = []
        countries = []
        for institution in authorship.get("institutions") or []:
            if institution.get("display_name"):
                institutions.append(institution["display_name"])
            if institution.get("country_code"):
                countries.append(institution["country_code"])

        records.append(
            {
                "author": author_name,
                "institutions": unique_strings(institutions),
                "countries": unique_strings(countries),
                "raw_affiliations": unique_strings(
                    authorship.get("raw_affiliation_strings")
                ),
            }
        )
    return records


class DailyArxivPipeline:
    def __init__(self):
        self.page_size = 100
        self.client = arxiv.Client(self.page_size)
        self.session = requests.Session()
        self.openalex_cache = {}

    def query_openalex(self, params, spider):
        """Run an OpenAlex query and fail open when the service is unavailable."""
        try:
            response = self.session.get(
                OPENALEX_API_URL,
                params=params,
                timeout=OPENALEX_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json().get("results") or []
        except (requests.RequestException, ValueError) as error:
            spider.logger.warning("OpenAlex query failed: %s", error)
            return []

    def fetch_openalex_work(self, arxiv_id, title, spider):
        """Fetch the OpenAlex work that corresponds to an arXiv identifier."""
        normalized_id = re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE)
        if normalized_id in self.openalex_cache:
            return self.openalex_cache[normalized_id]

        doi = f"10.48550/arxiv.{normalized_id.lower()}"
        mailto = os.environ.get("OPENALEX_MAILTO") or os.environ.get("EMAIL")
        common_params = {"per-page": 5}
        if mailto:
            common_params["mailto"] = mailto

        results = self.query_openalex(
            {**common_params, "filter": f"doi:{doi}"},
            spider,
        )
        work = results[0] if results else None

        # Some valid arXiv records are missing the DataCite DOI in OpenAlex.
        # Fall back to an exact normalized-title match rather than dropping
        # potentially useful affiliation data.
        if not work and title:
            results = self.query_openalex(
                {**common_params, "filter": f"title.search:{title}"},
                spider,
            )
            normalized_title = normalize_title(title)
            work = next(
                (
                    result
                    for result in results
                    if normalize_title(result.get("title")) == normalized_title
                ),
                None,
            )

        self.openalex_cache[normalized_id] = work
        return work

    def process_item(self, item: dict, spider):
        item["pdf"] = f"https://arxiv.org/pdf/{item['id']}"
        item["abs"] = f"https://arxiv.org/abs/{item['id']}"
        search = arxiv.Search(
            id_list=[item["id"]],
        )
        paper = next(self.client.results(search))
        item["authors"] = [a.name for a in paper.authors]
        item["title"] = paper.title
        item["categories"] = paper.categories
        item["comment"] = paper.comment
        item["summary"] = paper.summary
        openalex_work = self.fetch_openalex_work(item["id"], item["title"], spider)
        item["author_affiliations"] = extract_author_affiliations(openalex_work)
        return item
