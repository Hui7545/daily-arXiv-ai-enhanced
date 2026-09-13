"""Batch-enrich crawled arXiv IDs with metadata and OpenAlex affiliations."""

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import types

import arxiv

from daily_arxiv.pipelines import (
    DailyArxivPipeline,
    extract_author_affiliations,
)


ARXIV_BATCH_SIZE = 100


def normalize_arxiv_id(value):
    """Normalize arxiv ids from API paths like /abs/2609.10750v1."""
    text = str(value or "")
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return re.sub(r"v\d+$", "", text, flags=re.IGNORECASE)


def chunk_ids(ids, size=ARXIV_BATCH_SIZE):
    """Yield id batches small enough for one arXiv API request."""
    for start in range(0, len(ids), size):
        yield ids[start : start + size]


def load_items(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def write_items(items, path):
    """Atomically rewrite the jsonl file after enrichment."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".enrich-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def fetch_arxiv_records(ids):
    """Fetch arXiv metadata by id_list batches instead of one call per paper."""
    records = {}
    client = arxiv.Client()
    for batch in chunk_ids(ids):
        search = arxiv.Search(
            id_list=batch,
            max_results=len(batch),
        )
        for result in client.results(search):
            records[normalize_arxiv_id(result.entry_id)] = result
    return records


def enrich_item(item, paper, openalex_pipeline, logger):
    """Add full arXiv metadata and OpenAlex affiliations to one raw record."""
    item["pdf"] = f"https://arxiv.org/pdf/{item['id']}"
    item["abs"] = f"https://arxiv.org/abs/{item['id']}"
    item["authors"] = [author.name for author in paper.authors]
    item["title"] = paper.title
    item["categories"] = paper.categories
    item["comment"] = paper.comment
    item["summary"] = paper.summary
    openalex_work = openalex_pipeline.fetch_openalex_work(
        item["id"],
        item["title"],
        types.SimpleNamespace(logger=logger),
    )
    item["author_affiliations"] = extract_author_affiliations(openalex_work)
    return item


def main():
    parser = argparse.ArgumentParser(
        description="Batch enrich arXiv id jsonl with metadata and affiliations."
    )
    parser.add_argument("--data", required=True, help="path to raw arXiv jsonl")
    args = parser.parse_args()

    items = load_items(args.data)
    logger = logging.getLogger("batch-embetter")
    logging.basicConfig(level=logging.WARNING)
    if not items:
        print("No papers to enrich.", file=sys.stderr)
        sys.exit(1)

    records = fetch_arxiv_records([item["id"] for item in items])
    missing = [item["id"] for item in items if normalize_arxiv_id(item["id"]) not in records]
    if missing:
        raise RuntimeError(
            f"Could not fetch metadata for {len(missing)} papers: {missing[:5]}"
        )

    pipeline = DailyArxivPipeline()
    enriched = [
        enrich_item(item, records[normalize_arxiv_id(item["id"])], pipeline, logger)
        for item in items
    ]
    write_items(enriched, args.data)
    print(f"enriched: {len(enriched)} papers in {args.data}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Enrichment failed: {error}", file=sys.stderr)
        sys.exit(1)
