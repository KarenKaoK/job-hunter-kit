from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from job_hunter_kit.models import (
    FilterResult,
    JobPosting,
    JobRunResult,
    JobStateEntry,
    JobStateStatus,
)


STATE_FIELDNAMES = [
    "job_key",
    "status",
    "first_seen_at",
    "last_seen_at",
    "title",
    "company",
    "location",
    "source",
    "url",
    "notes",
]


def job_key(job: JobPosting) -> str:
    if job.url:
        return f"url:{job.url.casefold()}"
    if job.id:
        return f"id:{job.source.casefold()}:{job.id.casefold()}"

    return "job:" + "|".join(
        [
            job.source.casefold(),
            job.title.casefold(),
            job.company.casefold(),
            job.location.casefold(),
        ]
    )


def load_job_state(path: str | Path) -> dict[str, JobStateEntry]:
    state_path = Path(path)
    if not state_path.exists():
        return {}

    with state_path.open("r", encoding="utf-8", newline="") as file:
        rows = csv.DictReader(file)
        return {
            row["job_key"]: _state_entry_from_row(row)
            for row in rows
            if row.get("job_key")
        }


def save_job_state(path: str | Path, state: dict[str, JobStateEntry]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with state_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=STATE_FIELDNAMES)
        writer.writeheader()
        for entry in sorted(state.values(), key=lambda item: item.first_seen_at):
            writer.writerow(_state_entry_to_row(entry))


def apply_job_state(
    results: list[FilterResult],
    state: dict[str, JobStateEntry],
    seen_at: str,
) -> list[JobRunResult]:
    run_results: list[JobRunResult] = []

    for result in results:
        key = job_key(result.job)
        existing_entry = state.get(key)
        status = existing_entry.status if existing_entry else "new"
        first_collected_at = existing_entry.first_seen_at if existing_entry else seen_at
        run_results.append(
            JobRunResult(
                filter_result=result,
                job_key=key,
                status=status,
                first_collected_at=first_collected_at,
                last_collected_at=seen_at,
            )
        )

    return run_results


def update_job_state(
    run_results: list[JobRunResult],
    state: dict[str, JobStateEntry],
    seen_at: str,
) -> dict[str, JobStateEntry]:
    updated_state = dict(state)

    for run_result in run_results:
        job = run_result.filter_result.job
        existing_entry = updated_state.get(run_result.job_key)
        if existing_entry:
            updated_state[run_result.job_key] = replace(
                existing_entry,
                last_seen_at=seen_at,
                title=job.title,
                company=job.company,
                location=job.location,
                source=job.source,
                url=job.url or "",
            )
            continue

        updated_state[run_result.job_key] = JobStateEntry(
            job_key=run_result.job_key,
            status="seen",
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            title=job.title,
            company=job.company,
            location=job.location,
            source=job.source,
            url=job.url or "",
            notes="",
        )

    return updated_state


def _state_entry_from_row(row: dict[str, str]) -> JobStateEntry:
    status = _parse_status(row.get("status", "seen"))
    return JobStateEntry(
        job_key=row.get("job_key", ""),
        status=status,
        first_seen_at=row.get("first_seen_at", ""),
        last_seen_at=row.get("last_seen_at", ""),
        title=row.get("title", ""),
        company=row.get("company", ""),
        location=row.get("location", ""),
        source=row.get("source", ""),
        url=row.get("url", ""),
        notes=row.get("notes", ""),
    )


def _state_entry_to_row(entry: JobStateEntry) -> dict[str, str]:
    return {
        "job_key": entry.job_key,
        "status": entry.status,
        "first_seen_at": entry.first_seen_at,
        "last_seen_at": entry.last_seen_at,
        "title": entry.title,
        "company": entry.company,
        "location": entry.location,
        "source": entry.source,
        "url": entry.url,
        "notes": entry.notes,
    }


def _parse_status(value: str) -> JobStateStatus:
    if value == "applied":
        return "applied"
    return "seen"
