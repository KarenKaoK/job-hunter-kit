from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime

from job_hunter_kit.collectors import ScrapeJobsFunc, collect_jobs
from job_hunter_kit.config import load_search_config
from job_hunter_kit.filters import filter_jobs
from job_hunter_kit.io import save_filter_results_csv, save_job_run_results_csv
from job_hunter_kit.master_csv import (
    load_master_jobs,
    merge_master_jobs,
    save_master_jobs,
)
from job_hunter_kit.models import FilterResult, JobRunResult, MasterJobUpdate, SearchConfig
from job_hunter_kit.state import (
    apply_job_state,
    load_job_state,
    save_job_state,
    update_job_state,
)


def collect_and_filter_jobs(
    config: SearchConfig,
    scrape_jobs_func: ScrapeJobsFunc | None = None,
) -> list[FilterResult]:
    jobs = collect_jobs(config.collection, scrape_jobs_func=scrape_jobs_func)
    return filter_jobs(jobs, config)


def collect_filter_and_save_csv(
    config_path: str | Path,
    output_path: str | Path,
    scrape_jobs_func: ScrapeJobsFunc | None = None,
) -> list[FilterResult]:
    config = load_search_config(config_path)
    results = collect_and_filter_jobs(config, scrape_jobs_func=scrape_jobs_func)
    save_filter_results_csv(output_path, results)
    return results


def collect_filter_track_and_save_csv(
    config_path: str | Path,
    output_path: str | Path,
    state_path: str | Path,
    scrape_jobs_func: ScrapeJobsFunc | None = None,
    seen_at: str | None = None,
) -> list[JobRunResult]:
    config = load_search_config(config_path)
    filter_results = collect_and_filter_jobs(config, scrape_jobs_func=scrape_jobs_func)
    state = load_job_state(state_path)
    timestamp = seen_at or datetime.now(UTC).isoformat(timespec="seconds")
    run_results = apply_job_state(filter_results, state, timestamp)
    updated_state = update_job_state(run_results, state, timestamp)
    save_job_state(state_path, updated_state)
    save_job_run_results_csv(output_path, run_results)
    return run_results


def collect_filter_merge_master_csv(
    config_path: str | Path,
    output_path: str | Path,
    scrape_jobs_func: ScrapeJobsFunc | None = None,
    collected_at: str | None = None,
) -> MasterJobUpdate:
    config = load_search_config(config_path)
    filter_results = collect_and_filter_jobs(config, scrape_jobs_func=scrape_jobs_func)
    timestamp = collected_at or datetime.now(UTC).isoformat(timespec="seconds")
    existing_rows = load_master_jobs(output_path)
    update = merge_master_jobs(existing_rows, filter_results, timestamp)
    save_master_jobs(output_path, update.rows)
    return update
