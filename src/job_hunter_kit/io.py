from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from job_hunter_kit.models import FilterResult, JobPosting


def load_jobs(path: str | Path) -> list[JobPosting]:
    jobs_path = Path(path)
    with jobs_path.open("r", encoding="utf-8") as file:
        raw_jobs = json.load(file)

    if not isinstance(raw_jobs, list):
        raise ValueError("Jobs JSON must contain a list of job postings.")

    return [_parse_job(raw_job) for raw_job in raw_jobs]


def save_filter_results(path: str | Path, results: list[FilterResult]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump([asdict(result) for result in results], file, indent=2)
        file.write("\n")


def save_filter_results_csv(path: str | Path, results: list[FilterResult]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "decision",
        "title",
        "company",
        "location",
        "work_mode",
        "language",
        "source",
        "url",
        "matched_include_rules",
        "matched_exclude_rules",
        "reasons",
        "description",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_filter_result_csv_row(result) for result in results)


def _filter_result_csv_row(result: FilterResult) -> dict[str, str]:
    job = result.job
    return {
        "decision": result.decision,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "work_mode": job.work_mode or "",
        "language": job.language or "",
        "source": job.source,
        "url": job.url or "",
        "matched_include_rules": "; ".join(result.matched_include_rules),
        "matched_exclude_rules": "; ".join(result.matched_exclude_rules),
        "reasons": "; ".join(result.reasons),
        "description": job.description,
    }


def _parse_job(raw_job: Any) -> JobPosting:
    if not isinstance(raw_job, dict):
        raise ValueError("Each job posting must be a JSON object.")

    required_fields = ["id", "title", "company", "location", "source", "description"]
    missing_fields = [field for field in required_fields if field not in raw_job]
    if missing_fields:
        raise ValueError(f"Job posting missing required fields: {missing_fields}")

    return JobPosting(
        id=str(raw_job["id"]),
        title=str(raw_job["title"]),
        company=str(raw_job["company"]),
        location=str(raw_job["location"]),
        source=str(raw_job["source"]),
        description=str(raw_job["description"]),
        work_mode=_optional_string(raw_job.get("work_mode")),
        language=_optional_string(raw_job.get("language")),
        url=_optional_string(raw_job.get("url")),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
