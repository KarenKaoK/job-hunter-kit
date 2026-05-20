from __future__ import annotations

import argparse
from pathlib import Path

from job_hunter_kit.workflows import collect_filter_merge_master_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect LinkedIn jobs with JobSpy, filter them, and save CSV output."
    )
    parser.add_argument(
        "--config",
        default="config/search_job_config.yaml",
        help="Path to the YAML search config.",
    )
    parser.add_argument(
        "--output",
        default="output/linkedin_jobs.csv",
        help="Path to the editable master CSV output.",
    )
    args = parser.parse_args()

    update = collect_filter_merge_master_csv(args.config, args.output)

    print(f"Saved {len(update.rows)} total rows to {Path(args.output)}")
    print(f"Collected this run: {update.collected_count}")
    print(f"Included collected jobs: {update.included_count}")
    print(f"New total: {update.new_count}")
    print(f"Seen total: {update.seen_count}")
    print(f"Applied total: {update.applied_count}")
    print(f"Translated this run: {update.translated_count}")
    print(f"Reused translation: {update.reused_translation_count}")
    print(f"Translation failed: {update.translation_failed_count}")


if __name__ == "__main__":
    main()
