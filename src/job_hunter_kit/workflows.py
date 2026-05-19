from __future__ import annotations

from pathlib import Path

from job_hunter_kit.collectors import ScrapeJobsFunc, collect_jobs
from job_hunter_kit.config import load_search_config
from job_hunter_kit.filters import filter_jobs
from job_hunter_kit.io import save_filter_results_csv
from job_hunter_kit.models import FilterResult, SearchConfig


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
