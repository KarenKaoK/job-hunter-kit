from __future__ import annotations

import argparse

from job_hunter_kit.refresh import export_new_jobs_to_analyze


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export newly crawled jobs that are not in analyzed_jobs.csv."
    )
    parser.add_argument(
        "--crawl",
        default="output/linkedin_jobs.csv",
        help="Path to latest crawled jobs CSV.",
    )
    parser.add_argument(
        "--analyzed",
        default="data/analyzed_jobs.csv",
        help="Path to canonical analyzed jobs CSV.",
    )
    parser.add_argument(
        "--output",
        default="data/new_jobs_to_analyze.csv",
        help="Path to export new jobs requiring AI analysis.",
    )
    args = parser.parse_args()

    summary = export_new_jobs_to_analyze(
        crawl_path=args.crawl,
        analyzed_path=args.analyzed,
        output_path=args.output,
    )

    print(f"Crawled rows: {summary['crawled_total']}")
    print(f"Existing analyzed rows: {summary['analyzed_total']}")
    print(f"Exported new jobs: {summary['new_exported']}")
    print(f"Skipped crawled rows without key: {summary['crawled_invalid_key_rows']}")
    print(f"Existing analyzed rows without key: {summary['analyzed_invalid_key_rows']}")


if __name__ == "__main__":
    main()
