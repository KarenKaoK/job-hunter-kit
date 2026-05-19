from __future__ import annotations

from collections.abc import Callable
from typing import Any

from job_hunter_kit.models import CollectionConfig, JobPosting


ScrapeJobsFunc = Callable[..., Any]


def collect_jobs(
    config: CollectionConfig,
    scrape_jobs_func: ScrapeJobsFunc | None = None,
) -> list[JobPosting]:
    if not config.search_terms:
        return []

    scraper = scrape_jobs_func or _load_jobspy_scraper()
    jobs: list[JobPosting] = []

    for search_term in config.search_terms:
        raw_jobs = scraper(
            site_name=config.platforms,
            search_term=search_term,
            location=config.location,
            results_wanted=config.results_per_term,
            hours_old=config.hours_old,
            linkedin_fetch_description=config.linkedin_fetch_description,
        )
        jobs.extend(_parse_jobspy_records(raw_jobs))

    return _deduplicate_jobs(jobs)


def _load_jobspy_scraper() -> ScrapeJobsFunc:
    try:
        from jobspy import scrape_jobs
    except ImportError as error:
        raise RuntimeError(
            "Job collection requires python-jobspy. Install dependencies with "
            '`python -m pip install -e ".[dev]"`.'
        ) from error

    return scrape_jobs


def _parse_jobspy_records(raw_jobs: Any) -> list[JobPosting]:
    records = _records_from_jobspy_result(raw_jobs)
    return [_job_from_record(record) for record in records]


def _records_from_jobspy_result(raw_jobs: Any) -> list[dict[str, Any]]:
    if raw_jobs is None:
        return []

    if hasattr(raw_jobs, "to_dict"):
        records = raw_jobs.to_dict("records")
    else:
        records = raw_jobs

    if not isinstance(records, list):
        raise ValueError(
            "JobSpy result must be a list of records or DataFrame-like object."
        )

    return [record for record in records if isinstance(record, dict)]


def _job_from_record(record: dict[str, Any]) -> JobPosting:
    title = _string_value(record, "title") or "Untitled role"
    company = (
        _string_value(record, "company")
        or _string_value(record, "company_name")
        or "Unknown company"
    )
    location = _string_value(record, "location") or "Unknown location"
    url = _string_value(record, "job_url") or _string_value(record, "job_url_direct")
    job_id = (
        _string_value(record, "id")
        or _string_value(record, "job_id")
        or url
        or "|".join([title, company, location])
    )

    return JobPosting(
        id=job_id,
        title=title,
        company=company,
        location=location,
        source="linkedin",
        description=_string_value(record, "description") or "",
        work_mode=(
            _string_value(record, "work_mode")
            or _string_value(record, "job_type")
            or _string_value(record, "interval")
        ),
        language=None,
        url=url,
    )


def _string_value(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None

    string_value = str(value).strip()
    return string_value or None


def _deduplicate_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    deduplicated: list[JobPosting] = []
    seen_keys: set[str] = set()

    for job in jobs:
        key = _dedupe_key(job)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduplicated.append(job)

    return deduplicated


def _dedupe_key(job: JobPosting) -> str:
    if job.url:
        return f"url:{job.url.casefold()}"

    return "|".join(
        [
            job.title.casefold(),
            job.company.casefold(),
            job.location.casefold(),
        ]
    )
