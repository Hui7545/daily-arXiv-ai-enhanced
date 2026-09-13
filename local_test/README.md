# Local isolated test

`run.py` copies the source directories into a timestamped workspace under
`local_test/runs/`. All generated JSONL, Markdown, logs, and file lists stay in
that workspace. The repository's existing `data/` and `assets/` directories are
not modified.

The runner uses the project virtual environment. Run `uv sync` first if it does
not exist.

## Unit tests

No network or API key is required:

```powershell
.\.venv\Scripts\python.exe local_test\run.py --mode unit
```

## Crawl test

This exercises arXiv crawling, list-page metadata parsing, batch API fallback,
OpenAlex affiliation enrichment, output, and deduplication. It does not call
the LLM:

```powershell
.\.venv\Scripts\python.exe local_test\run.py --mode crawl --max-papers 5
```

Use `--max-papers 0` to remove the item limit.

## Full pipeline

This also calls the configured OpenAI-compatible model:

```powershell
.\.venv\Scripts\python.exe local_test\run.py --mode full --max-papers 5
```

The runner reads environment variables from the current shell and optionally
layers values from `ai/.env`. Required full-pipeline variables:

```text
OPENAI_API_KEY
OPENAI_BASE_URL
MODEL_NAME
LANGUAGE
```

`CATEGORIES` controls the crawled arXiv categories. `OPENALEX_MAILTO` or `EMAIL`
is used for the OpenAlex polite request pool.

Each run prints its workspace path. `run.log` contains the complete command
output, and generated files remain available after either success or failure.
