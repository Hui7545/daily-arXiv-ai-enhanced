"""Filter and rank the day's AI-enhanced papers by relevance/quality/priority.

Runs after AI enhancement, before markdown conversion. It hard-filters out papers
that the LLM judged unrelated to search, recommendation, advertising, or adjacent
topics, then sorts the survivors by `priority_score` descending. It rewrites the
input jsonl in place so downstream tools need no path changes.

Filtering rules key off the `AI` judgment fields produced by enhance.py:
- is_relevant: the hard gate. Papers not judged relevant are dropped. Historical
  records using is_recommendation_related remain supported as a fallback.
- is_high_quality: intentionally NOT a hard gate. Quality is a subjective LLM call
  that tends to be conservative and would wrongly purge many on-topic papers (a
  real DeepSeek run dropped 2 of 2 relevant papers this way). It is still reflected
  in priority_score, so it shapes ranking rather than inclusion.
"""

import argparse
import json
import os
import sys
import tempfile


def load_items(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def write_items(items, path):
    """Atomically rewrite a jsonl file so a mid-write crash never truncates it."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".filter-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def keep(item):
    """Return True when the paper should be published.

    Only `is_relevant` is a hard gate. `is_high_quality` deliberately
    does not exclude papers (see module docstring) and instead feeds ranking via
    priority_score.
    """
    ai = item.get("AI") or {}
    if "is_relevant" in ai:
        return ai.get("is_relevant", False)
    return ai.get("is_recommendation_related", False)


def priority(item):
    ai = item.get("AI") or {}
    try:
        return float(ai.get("priority_score", 0))
    except (TypeError, ValueError):
        return 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        required=True,
        help="path to {date}_AI_enhanced_{lang}.jsonl",
    )
    args = parser.parse_args()

    items = load_items(args.data)
    kept = [it for it in items if keep(it)]
    kept.sort(key=priority, reverse=True)
    dropped = len(items) - len(kept)

    # In-place atomic rewrite so downstream (convert.py + frontend) needs no changes.
    write_items(kept, args.data)

    print(
        f"filter: {len(items)} -> {len(kept)} kept, {dropped} dropped",
        file=sys.stderr,
    )
    # Signal "nothing survived" so the workflow can skip publishing an empty digest.
    if not kept and os.environ.get("FILTER_EXIT_ON_EMPTY", "1") == "1":
        sys.exit(1)


if __name__ == "__main__":
    main()
