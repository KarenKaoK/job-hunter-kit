from __future__ import annotations

import argparse

from job_hunter_kit.refresh import append_new_analyzed_jobs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append new analyzed jobs into canonical analyzed_jobs.csv."
    )
    parser.add_argument(
        "--analyzed",
        default="data/analyzed_jobs.csv",
        help="Path to canonical analyzed jobs CSV.",
    )
    parser.add_argument(
        "--new-analyzed",
        default="data/new_analyzed_jobs.csv",
        help="Path to newly AI-analyzed jobs CSV.",
    )
    args = parser.parse_args()

    summary = append_new_analyzed_jobs(
        analyzed_path=args.analyzed,
        new_analyzed_path=args.new_analyzed,
    )

    print(f"Existing rows before append: {summary['existing_total_before']}")
    print(f"New analyzed candidate rows: {summary['new_analyzed_total']}")
    print(f"Appended rows: {summary['appended']}")
    print(f"Skipped duplicates: {summary['duplicates_skipped']}")
    print(f"Skipped new rows without key: {summary['new_invalid_key_rows']}")
    print(f"Existing rows without key: {summary['existing_invalid_key_rows']}")
    print(f"Final total rows: {summary['final_total']}")


if __name__ == "__main__":
    main()
