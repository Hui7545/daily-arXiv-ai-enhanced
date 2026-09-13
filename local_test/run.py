#!/usr/bin/env python3
"""Run the project in an isolated local-test workspace."""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


LOCAL_TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = LOCAL_TEST_DIR.parent
SOURCE_DIRS = ("daily_arxiv", "ai", "to_md")


def project_python():
    """Return the project virtual-environment interpreter."""
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    python_name = "python.exe" if os.name == "nt" else "python"
    candidates = (
        REPO_ROOT / ".venv" / scripts_dir / python_name,
        Path(sys.executable),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Python environment not found. Run `uv sync` first.")


def load_env_file(path):
    """Read simple KEY=VALUE entries from an optional .env file."""
    if not path.is_file():
        return {}

    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values


def build_environment():
    """Layer ai/.env under the caller's environment without exposing secrets."""
    env = os.environ.copy()
    for key, value in load_env_file(REPO_ROOT / "ai" / ".env").items():
        env.setdefault(key, value)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def copy_sources(workspace):
    """Copy only code needed by the pipeline into the isolated workspace."""
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".env")
    for dirname in SOURCE_DIRS:
        shutil.copytree(
            REPO_ROOT / dirname,
            workspace / dirname,
            ignore=ignore,
        )
    (workspace / "data").mkdir()
    (workspace / "assets").mkdir()


def run_step(name, command, cwd, env, log_file, check=True):
    """Run one command while mirroring output to the terminal and a run log."""
    command_text = subprocess.list2cmdline([str(part) for part in command])
    banner = f"\n=== {name} ===\n$ {command_text}\n"
    print(banner, end="")
    log_file.write(banner)
    log_file.flush()

    process = subprocess.Popen(
        [str(part) for part in command],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        log_file.write(line)
        log_file.flush()
    return_code = process.wait()

    if check and return_code != 0:
        raise RuntimeError(f"{name} failed with exit code {return_code}")
    return return_code


def run_unit_tests(python, workspace, env, log_file):
    run_step(
        "AI unit tests",
        [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
        workspace / "ai",
        env,
        log_file,
    )
    run_step(
        "Scrapy pipeline unit tests",
        [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
        workspace / "daily_arxiv",
        env,
        log_file,
    )


def crawl(python, workspace, env, log_file, date, max_papers):
    crawl_env = env.copy()
    crawl_env["ARXIV_MAX_PAPERS"] = str(max_papers)
    command = [
        python,
        "-m",
        "scrapy",
        "crawl",
        "arxiv",
        "-o",
        f"../data/{date}.jsonl",
    ]

    run_step(
        "Crawl arXiv",
        command,
        workspace / "daily_arxiv",
        crawl_env,
        log_file,
    )

    data_file = workspace / "data" / f"{date}.jsonl"
    if not data_file.is_file() or data_file.stat().st_size == 0:
        raise RuntimeError(f"Crawl produced no data: {data_file}")

    return data_file


def deduplicate(python, workspace, env, log_file):
    return_code = run_step(
        "Deduplicate papers",
        [python, "daily_arxiv/check_stats.py"],
        workspace / "daily_arxiv",
        env,
        log_file,
        check=False,
    )
    if return_code == 1:
        print("\nNo new papers survived deduplication.")
        return False
    if return_code != 0:
        raise RuntimeError(
            f"Deduplication failed with exit code {return_code}"
        )
    return True


def enrich_metadata(python, workspace, env, log_file, date):
    run_step(
        "Batch enrich metadata",
        [
            python,
            "daily_arxiv/enrich.py",
            "--data",
            f"data/{date}.jsonl",
        ],
        workspace,
        env,
        log_file,
    )


def enhance_filter_and_convert(
    python,
    workspace,
    env,
    log_file,
    date,
):
    language = env.get("LANGUAGE", "Chinese")
    ai_file = (
        workspace
        / "data"
        / f"{date}_AI_enhanced_{language}.jsonl"
    )

    run_step(
        "AI enhancement",
        [python, "enhance.py", "--data", f"../data/{date}.jsonl"],
        workspace / "ai",
        env,
        log_file,
    )
    filter_code = run_step(
        "Filter and rank papers",
        [python, "filter.py", "--data", f"../data/{ai_file.name}"],
        workspace / "ai",
        env,
        log_file,
        check=False,
    )
    if filter_code == 1:
        print("\nAll AI-enhanced papers were filtered out.")
        return
    if filter_code != 0:
        raise RuntimeError(f"Filtering failed with exit code {filter_code}")

    run_step(
        "Convert to Markdown",
        [python, "convert.py", "--data", f"../data/{ai_file.name}"],
        workspace / "to_md",
        env,
        log_file,
    )

    file_list = workspace / "assets" / "file-list.txt"
    file_list.write_text(
        "\n".join(
            sorted(path.name for path in (workspace / "data").glob("*.jsonl"))
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run local tests in an isolated workspace."
    )
    parser.add_argument(
        "--mode",
        choices=("unit", "crawl", "full"),
        default="unit",
        help=(
            "unit: no network; crawl: crawl and deduplicate; "
            "full: crawl, enhance, filter, and convert"
        ),
    )
    parser.add_argument(
        "--date",
        help="Run date in YYYY-MM-DD format (default: local today)",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=5,
        help=(
            "Maximum crawled papers; use 0 for no limit "
            "(default: 5)"
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.max_papers < 0:
        raise ValueError("--max-papers must be zero or greater")

    python = project_python()
    run_date = args.date or datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    workspace = LOCAL_TEST_DIR / "runs" / timestamp
    workspace.mkdir(parents=True)
    copy_sources(workspace)
    env = build_environment()

    print(f"Isolated workspace: {workspace}")
    print(f"Python: {python}")

    log_path = workspace / "run.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        if args.mode == "unit":
            run_unit_tests(python, workspace, env, log_file)
        else:
            crawl(
                python,
                workspace,
                env,
                log_file,
                run_date,
                args.max_papers,
            )
            if deduplicate(python, workspace, env, log_file):
                enrich_metadata(
                    python,
                    workspace,
                    env,
                    log_file,
                    run_date,
                )
                if args.mode == "full":
                    enhance_filter_and_convert(
                        python,
                        workspace,
                        env,
                        log_file,
                        run_date,
                    )

    print(f"\nLocal test completed. Results: {workspace}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print(f"\nLocal test failed: {error}", file=sys.stderr)
        sys.exit(1)
