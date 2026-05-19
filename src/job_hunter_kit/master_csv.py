from __future__ import annotations

import csv
import re
from dataclasses import replace
from pathlib import Path

from job_hunter_kit.models import FilterResult, JobPosting, MasterJobRow, MasterJobUpdate


MASTER_FIELDNAMES = [
    "status",
    "job_id",
    "first_collected_at",
    "last_collected_at",
    "title",
    "company",
    "location",
    "work_mode",
    "language",
    "source",
    "url",
    "description",
    "notes",
]


def load_master_jobs(path: str | Path) -> list[MasterJobRow]:
    master_path = Path(path)
    if not master_path.exists():
        return []

    with master_path.open("r", encoding="utf-8", newline="") as file:
        return [_row_from_csv(row) for row in csv.DictReader(file)]


def save_master_jobs(path: str | Path, rows: list[MasterJobRow]) -> None:
    master_path = Path(path)
    master_path.parent.mkdir(parents=True, exist_ok=True)

    with master_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MASTER_FIELDNAMES)
        writer.writeheader()
        writer.writerows(_row_to_csv(row) for row in rows)


def merge_master_jobs(
    existing_rows: list[MasterJobRow],
    filter_results: list[FilterResult],
    collected_at: str,
) -> MasterJobUpdate:
    existing_by_id = {row.job_id: row for row in existing_rows}
    merged_by_id = dict(existing_by_id)
    included_results = [
        result for result in filter_results if result.decision == "include"
    ]

    for result in included_results:
        job = result.job
        row_id = master_job_id(job)
        existing_row = existing_by_id.get(row_id)
        if existing_row:
            merged_by_id[row_id] = _updated_existing_row(
                existing_row,
                job,
                collected_at,
            )
        else:
            merged_by_id[row_id] = _new_master_row(job, row_id, collected_at)

    rows = sorted(
        merged_by_id.values(),
        key=lambda row: (row.first_collected_at, row.company.casefold(), row.title.casefold()),
    )
    return MasterJobUpdate(
        rows=rows,
        collected_count=len(filter_results),
        included_count=len(included_results),
        new_count=sum(row.status == "new" for row in rows),
        seen_count=sum(row.status == "seen" for row in rows),
        applied_count=sum(row.status == "applied" for row in rows),
    )


def master_job_id(job: JobPosting) -> str:
    source = job.source.casefold()
    url_id = _linkedin_id_from_url(job.url or "")
    if url_id:
        return f"{source}:{url_id}"

    if job.id and not _looks_like_url(job.id) and "|" not in job.id:
        return f"{source}:{_slug(job.id)}"

    id_url_id = _linkedin_id_from_url(job.id)
    if id_url_id:
        return f"{source}:{id_url_id}"

    return f"{source}:{_slug('-'.join([job.title, job.company, job.location]))}"


def _updated_existing_row(
    existing_row: MasterJobRow,
    job: JobPosting,
    collected_at: str,
) -> MasterJobRow:
    status = "applied" if existing_row.status == "applied" else "seen"
    return replace(
        existing_row,
        status=status,
        last_collected_at=collected_at,
        title=job.title,
        company=job.company,
        location=job.location,
        work_mode=job.work_mode or "",
        language=job.language or "",
        source=job.source,
        url=job.url or "",
        description=job.description,
    )


def _new_master_row(
    job: JobPosting,
    row_id: str,
    collected_at: str,
) -> MasterJobRow:
    return MasterJobRow(
        status="new",
        job_id=row_id,
        first_collected_at=collected_at,
        last_collected_at=collected_at,
        title=job.title,
        company=job.company,
        location=job.location,
        work_mode=job.work_mode or "",
        language=job.language or "",
        source=job.source,
        url=job.url or "",
        description=job.description,
        notes="",
    )


def _row_from_csv(row: dict[str, str]) -> MasterJobRow:
    return MasterJobRow(
        status=_parse_status(row.get("status", "seen")),
        job_id=row.get("job_id", ""),
        first_collected_at=row.get("first_collected_at", ""),
        last_collected_at=row.get("last_collected_at", ""),
        title=row.get("title", ""),
        company=row.get("company", ""),
        location=row.get("location", ""),
        work_mode=row.get("work_mode", ""),
        language=row.get("language", ""),
        source=row.get("source", ""),
        url=row.get("url", ""),
        description=row.get("description", ""),
        notes=row.get("notes", ""),
    )


def _row_to_csv(row: MasterJobRow) -> dict[str, str]:
    return {
        "status": row.status,
        "job_id": row.job_id,
        "first_collected_at": row.first_collected_at,
        "last_collected_at": row.last_collected_at,
        "title": row.title,
        "company": row.company,
        "location": row.location,
        "work_mode": row.work_mode,
        "language": row.language,
        "source": row.source,
        "url": row.url,
        "description": row.description,
        "notes": row.notes,
    }


def _parse_status(value: str) -> str:
    if value == "applied":
        return "applied"
    if value == "new":
        return "new"
    return "seen"


def _linkedin_id_from_url(value: str) -> str | None:
    match = re.search(r"/(?:jobs/)?view/([^/?#]+)", value)
    if match:
        return _slug(match.group(1))
    return None


def _looks_like_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.casefold()).strip("-")
    return slug or "unknown"
