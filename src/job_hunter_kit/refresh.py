from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import urlparse


EXPORT_COLUMNS = [
    "job_id",
    "title",
    "company",
    "location",
    "url",
    "description",
    "description_hash",
    "source",
    "collected_at",
]

USER_EDIT_FIELDS = [
    "application_status",
    "applied_date",
    "notes",
    "status_updated_at",
]


def key_from_row(row: dict[str, str]) -> str | None:
    job_id = _first_non_empty(row, ["job_id", "Job ID"])
    url = _first_non_empty(row, ["url", "URL", "Job Link"])
    linkedin_id = _linkedin_job_id(job_id) or _linkedin_job_id(url)
    if linkedin_id:
        return f"linkedin:{linkedin_id}"

    normalized_job_id = _normalize_job_id(job_id)
    if normalized_job_id:
        return f"job_id:{normalized_job_id}"

    normalized_url = _normalize_url(url)
    if normalized_url:
        return f"url:{normalized_url}"

    return None


def read_csv_rows(path: str | Path) -> tuple[list[dict[str, str]], list[str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return [], []

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    return rows, fieldnames


def write_csv_rows(path: str | Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_new_jobs_to_analyze(
    crawl_path: str | Path,
    analyzed_path: str | Path,
    output_path: str | Path,
) -> dict[str, int]:
    crawled_rows, _ = read_csv_rows(crawl_path)
    analyzed_rows, _ = read_csv_rows(analyzed_path)

    analyzed_keys: set[str] = set()
    analyzed_invalid = 0
    for row in analyzed_rows:
        key = key_from_row(row)
        if key is None:
            analyzed_invalid += 1
            continue
        analyzed_keys.add(key)

    export_rows: list[dict[str, str]] = []
    crawled_invalid = 0
    for row in crawled_rows:
        key = key_from_row(row)
        if key is None:
            crawled_invalid += 1
            continue
        if key in analyzed_keys:
            continue
        export_rows.append(
            {
                "job_id": row.get("job_id", ""),
                "title": row.get("title", ""),
                "company": row.get("company", ""),
                "location": row.get("location", ""),
                "url": row.get("url", ""),
                "description": row.get("description", ""),
                "description_hash": row.get("description_hash", ""),
                "source": row.get("source", ""),
                "collected_at": row.get("collected_at")
                or row.get("last_collected_at", "")
                or "",
            }
        )

    write_csv_rows(output_path, export_rows, EXPORT_COLUMNS)
    return {
        "crawled_total": len(crawled_rows),
        "analyzed_total": len(analyzed_rows),
        "analyzed_invalid_key_rows": analyzed_invalid,
        "crawled_invalid_key_rows": crawled_invalid,
        "new_exported": len(export_rows),
    }


def append_new_analyzed_jobs(
    analyzed_path: str | Path,
    new_analyzed_path: str | Path,
) -> dict[str, int]:
    existing_rows, existing_fields = read_csv_rows(analyzed_path)
    new_rows, new_fields = read_csv_rows(new_analyzed_path)

    existing_keys: set[str] = set()
    existing_invalid = 0
    for row in existing_rows:
        key = key_from_row(row)
        if key is None:
            existing_invalid += 1
            continue
        existing_keys.add(key)

    output_fields = _merge_fieldnames(existing_fields, new_fields)
    for field in USER_EDIT_FIELDS:
        if field not in output_fields:
            output_fields.append(field)

    appended = 0
    duplicate_skipped = 0
    invalid_new = 0

    for row in new_rows:
        key = key_from_row(row)
        if key is None:
            invalid_new += 1
            continue
        if key in existing_keys:
            duplicate_skipped += 1
            continue

        new_row: dict[str, str] = {}
        for field in output_fields:
            new_row[field] = row.get(field, "")

        status_value = (new_row.get("application_status") or "").strip()
        if not status_value:
            new_row["application_status"] = "Not Applied"
        new_row["applied_date"] = new_row.get("applied_date", "")
        new_row["notes"] = new_row.get("notes", "")
        new_row["status_updated_at"] = new_row.get("status_updated_at", "")

        existing_rows.append(new_row)
        existing_keys.add(key)
        appended += 1

    normalized_rows = [_normalize_row(row, output_fields) for row in existing_rows]
    write_csv_rows(analyzed_path, normalized_rows, output_fields)

    return {
        "existing_total_before": len(existing_rows) - appended,
        "new_analyzed_total": len(new_rows),
        "existing_invalid_key_rows": existing_invalid,
        "new_invalid_key_rows": invalid_new,
        "duplicates_skipped": duplicate_skipped,
        "appended": appended,
        "final_total": len(normalized_rows),
    }


def dedupe_analyzed_jobs_file(
    analyzed_path: str | Path,
    apply: bool = False,
) -> dict[str, int]:
    rows, fieldnames = read_csv_rows(analyzed_path)
    if not rows:
        return {
            "input_rows": 0,
            "output_rows": 0,
            "duplicates_removed": 0,
            "invalid_key_rows": 0,
        }

    deduped_rows: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    invalid_key_rows = 0

    for row in rows:
        key = key_from_row(row)
        if key is None:
            invalid_key_rows += 1
            deduped_rows.append(row)
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_rows.append(row)

    duplicates_removed = len(rows) - len(deduped_rows)
    if apply:
        write_csv_rows(analyzed_path, deduped_rows, fieldnames)

    return {
        "input_rows": len(rows),
        "output_rows": len(deduped_rows),
        "duplicates_removed": duplicates_removed,
        "invalid_key_rows": invalid_key_rows,
    }


def _merge_fieldnames(existing_fields: list[str], new_fields: list[str]) -> list[str]:
    merged: list[str] = []
    for fields in (existing_fields, new_fields):
        for field in fields:
            if field and field not in merged:
                merged.append(field)
    return merged


def _normalize_row(row: dict[str, str], fieldnames: list[str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for field in fieldnames:
        normalized[field] = row.get(field, "")
    return normalized


def _first_non_empty(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def _linkedin_job_id(value: str) -> str:
    if not value:
        return ""

    text = value.strip()
    prefixed = re.fullmatch(r"linkedin:(\d+)", text, flags=re.IGNORECASE)
    if prefixed:
        return prefixed.group(1)

    numeric = re.fullmatch(r"\d+", text)
    if numeric:
        return numeric.group(0)

    url_match = re.search(r"/jobs/view/(\d+)", text)
    if url_match:
        return url_match.group(1)

    return ""


def _normalize_job_id(job_id: str) -> str:
    return job_id.strip().casefold()


def _normalize_url(url: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url.strip())
    if not parsed.scheme and not parsed.netloc:
        return url.strip().casefold()

    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
