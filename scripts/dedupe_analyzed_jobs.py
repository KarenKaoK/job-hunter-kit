from __future__ import annotations

import argparse
from pathlib import Path

from job_hunter_kit.refresh import dedupe_analyzed_jobs_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove duplicate rows in analyzed_jobs.csv using canonical keys."
    )
    parser.add_argument(
        "--analyzed",
        default="data/analyzed_jobs.csv",
        help="Path to canonical analyzed jobs CSV.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to file. Default is dry-run.",
    )
    args = parser.parse_args()

    summary = dedupe_analyzed_jobs_file(args.analyzed, apply=args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Mode: {mode}")
    print(f"Input rows: {summary['input_rows']}")
    print(f"Output rows: {summary['output_rows']}")
    print(f"Duplicate rows removed: {summary['duplicates_removed']}")
    print(f"Rows without key: {summary['invalid_key_rows']}")
    print(f"Output file: {Path(args.analyzed)}")


if __name__ == "__main__":
    main()
