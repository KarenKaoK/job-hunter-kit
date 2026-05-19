from __future__ import annotations

import argparse
from pathlib import Path

from job_hunter_kit.workflows import collect_filter_and_save_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect LinkedIn jobs with JobSpy, filter them, and save CSV output."
    )
    parser.add_argument(
        "--config",
        default="examples/search_job_config.example.yaml",
        help="Path to the YAML search config.",
    )
    parser.add_argument(
        "--output",
        default="output/linkedin_jobs_filtered.csv",
        help="Path to write the filtered CSV output.",
    )
    args = parser.parse_args()

    results = collect_filter_and_save_csv(args.config, args.output)
    included_count = sum(result.decision == "include" for result in results)
    excluded_count = sum(result.decision == "exclude" for result in results)

    print(f"Saved {len(results)} results to {Path(args.output)}")
    print(f"Included: {included_count}")
    print(f"Excluded: {excluded_count}")


if __name__ == "__main__":
    main()
