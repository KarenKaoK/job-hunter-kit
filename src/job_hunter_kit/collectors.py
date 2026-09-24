from __future__ import annotations

import json
import logging
import re
import warnings
from collections.abc import Callable
from typing import Any
from urllib.parse import quote_plus

from job_hunter_kit.models import CollectionConfig, JobPosting


ScrapeJobsFunc = Callable[..., Any]
log = logging.getLogger(__name__)

GLASSDOOR_LOCATION_FALLBACKS = {
    ("germany", "berlin"): (2622109, "CITY"),
    ("germany", "munich"): (4990924, "CITY"),
    ("germany", "münchen"): (4990924, "CITY"),
}


def collect_jobs(
    config: CollectionConfig,
    scrape_jobs_func: ScrapeJobsFunc | None = None,
) -> list[JobPosting]:
    if not config.search_terms:
        return []

    scraper = scrape_jobs_func or _load_jobspy_scraper()
    jobs: list[JobPosting] = []

    for location in _collection_locations(config):
        for search_term in config.search_terms:
            for platform in config.platforms:
                scrape_kwargs = _scrape_kwargs(config, platform, location, search_term)
                try:
                    raw_jobs = scraper(**scrape_kwargs)
                except Exception as error:
                    warnings.warn(
                        (
                            f"JobSpy {platform} collection failed for "
                            f"{search_term!r} in {location!r}: {error}"
                        ),
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    continue

                jobs.extend(
                    _parse_jobspy_records(
                        raw_jobs,
                        default_source=_default_source([platform]),
                    )
                )

    return _deduplicate_jobs(jobs)


def _collection_locations(config: CollectionConfig) -> list[str]:
    return config.locations or [config.location]


def _scrape_kwargs(
    config: CollectionConfig,
    platform: str,
    location: str,
    search_term: str,
) -> dict[str, Any]:
    scrape_kwargs = dict(
        site_name=[platform],
        search_term=search_term,
        location=location,
        results_wanted=config.results_per_term,
        hours_old=config.hours_old,
    )
    if platform == "linkedin":
        scrape_kwargs["linkedin_fetch_description"] = config.linkedin_fetch_description
    if platform == "glassdoor":
        scrape_kwargs["country_indeed"] = config.country_indeed

    return scrape_kwargs


def _load_jobspy_scraper() -> ScrapeJobsFunc:
    try:
        from jobspy import scrape_jobs
        from jobspy.glassdoor import Glassdoor
        from jobspy.glassdoor.constant import query_template
    except ImportError as error:
        raise RuntimeError(
            "Job collection requires python-jobspy. Install dependencies with "
            '`python -m pip install -e ".[dev]"`.'
        ) from error

    _patch_jobspy_glassdoor_scraper(Glassdoor, query_template)
    return scrape_jobs


def _patch_jobspy_glassdoor_scraper(
    glassdoor_cls: Any,
    query_template: str = "",
) -> None:
    if getattr(glassdoor_cls, "_job_hunter_kit_glassdoor_patched", False):
        return

    def get_csrf_token_from_homepage(self: Any) -> str | None:
        res = self.session.get(_glassdoor_url(self.base_url, "/"))
        matches = re.findall(r'"token":\s*"([^"]+)"', res.text)
        if matches:
            return matches[0]
        return None

    def get_location_with_fallback(
        self: Any,
        location: str,
        is_remote: bool,
    ) -> tuple[int | str | None, str | None]:
        if not location or is_remote:
            return "11047", "STATE"

        url = _glassdoor_url(
            self.base_url,
            (
                "/findPopularLocationAjax.htm"
                f"?maxLocationsToReturn=10&term={quote_plus(location)}"
            ),
        )
        res = self.session.get(url)
        if res.status_code == 200:
            items = res.json()
            if not items:
                raise ValueError(f"Location '{location}' not found on Glassdoor")
            location_type = _glassdoor_location_type(items[0]["locationType"])
            return int(items[0]["locationId"]), location_type

        fallback = _glassdoor_location_fallback(self, location)
        if fallback:
            log.info(
                "Glassdoor location lookup returned %s for %r; using configured "
                "location fallback.",
                res.status_code,
                location,
            )
            return fallback

        if res.status_code == 429:
            warnings.warn(
                "Glassdoor returned 429 while resolving location.",
                RuntimeWarning,
                stacklevel=2,
            )
        else:
            warnings.warn(
                (
                    f"Glassdoor returned {res.status_code} while resolving "
                    f"location {location!r}."
                ),
                RuntimeWarning,
                stacklevel=2,
            )
        return None, None

    glassdoor_cls._get_csrf_token = get_csrf_token_from_homepage
    glassdoor_cls._get_location = get_location_with_fallback
    glassdoor_cls._add_payload = _glassdoor_add_payload(query_template)
    glassdoor_cls._fetch_jobs_page = _glassdoor_fetch_jobs_page()
    glassdoor_cls._job_hunter_kit_glassdoor_patched = True


def _glassdoor_fetch_jobs_page() -> Callable[..., tuple[list[Any], str | None]]:
    def fetch_jobs_page(
        self: Any,
        scraper_input: Any,
        location_id: int,
        location_type: str,
        page_num: int,
        cursor: str | None,
    ) -> tuple[list[Any], str | None]:
        payload = self._add_payload(location_id, location_type, page_num, cursor)
        response = self.session.post(
            _glassdoor_url(self.base_url, "/graph"),
            timeout_seconds=15,
            data=payload,
        )

        if response.status_code != 200:
            warnings.warn(
                _glassdoor_response_warning(
                    response=response,
                    payload=payload,
                    scraper_input=scraper_input,
                    location_id=location_id,
                    location_type=location_type,
                ),
                RuntimeWarning,
                stacklevel=2,
            )
            return [], None

        try:
            response_json = response.json()[0]
        except Exception as error:
            warnings.warn(
                f"Glassdoor returned invalid JSON: {error}",
                RuntimeWarning,
                stacklevel=2,
            )
            return [], None

        fatal_errors = _glassdoor_fatal_graphql_errors(response_json)
        if fatal_errors:
            warnings.warn(
                f"Glassdoor returned jobListings GraphQL errors: {fatal_errors}",
                RuntimeWarning,
                stacklevel=2,
            )
            return [], None

        jobs_data = (
            response_json.get("data", {})
            .get("jobListings", {})
            .get("jobListings", [])
        )
        jobs = []
        for job_data in jobs_data:
            try:
                job = self._process_job(job_data)
            except Exception as error:
                warnings.warn(
                    f"Glassdoor failed to process a job row: {error}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            if job:
                jobs.append(job)

        next_cursor = _glassdoor_cursor_for_page(
            response_json.get("data", {})
            .get("jobListings", {})
            .get("paginationCursors", []),
            page_num + 1,
        )
        return jobs, next_cursor

    return fetch_jobs_page


def _glassdoor_response_warning(
    response: Any,
    payload: str,
    scraper_input: Any,
    location_id: int,
    location_type: str,
) -> str:
    variables = _glassdoor_payload_variables(payload)
    response_text = str(getattr(response, "text", "") or "")
    response_snippet = re.sub(r"\s+", " ", response_text).strip()[:500]
    return (
        "Glassdoor GraphQL request failed: "
        f"status={getattr(response, 'status_code', 'unknown')}; "
        f"url={getattr(response, 'url', '<unknown>')}; "
        f"search_term={getattr(scraper_input, 'search_term', '')!r}; "
        f"location={getattr(scraper_input, 'location', '')!r}; "
        f"location_id={location_id}; "
        f"location_type={location_type}; "
        f"parameterUrlInput={variables.get('parameterUrlInput', '')!r}; "
        f"filterParams={variables.get('filterParams', [])!r}; "
        f"response_snippet={response_snippet!r}"
    )


def _glassdoor_payload_variables(payload: str) -> dict[str, Any]:
    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if not parsed_payload:
        return {}
    variables = parsed_payload[0].get("variables", {})
    if isinstance(variables, dict):
        return variables
    return {}


def _glassdoor_fatal_graphql_errors(response_json: dict[str, Any]) -> list[Any]:
    errors = response_json.get("errors", [])
    return [
        error
        for error in errors
        if "jobListings" in str(error.get("path", []))
        and "jobsPageSeoData" not in str(error.get("path", []))
    ]


def _glassdoor_cursor_for_page(
    pagination_cursors: list[dict[str, Any]],
    page_num: int,
) -> str | None:
    for cursor_data in pagination_cursors:
        if cursor_data.get("pageNumber") == page_num:
            return cursor_data.get("cursor")
    return None


def _glassdoor_add_payload(query_template: str) -> Callable[..., str]:
    def add_payload(
        self: Any,
        location_id: int,
        location_type: str,
        page_num: int,
        cursor: str | None = None,
    ) -> str:
        fromage = None
        if self.scraper_input.hours_old:
            fromage = max(self.scraper_input.hours_old // 24, 1)

        filter_params = []
        if self.scraper_input.easy_apply:
            filter_params.append({"filterKey": "applicationType", "values": "1"})
        if fromage:
            filter_params.append({"filterKey": "fromAge", "values": str(fromage)})
        if self.scraper_input.job_type:
            filter_params.append(
                {"filterKey": "jobType", "values": self.scraper_input.job_type.value[0]}
            )

        payload = {
            "operationName": "JobSearchResultsQuery",
            "variables": {
                "excludeJobListingIds": [],
                "filterParams": filter_params,
                "keyword": self.scraper_input.search_term,
                "numJobsToShow": 30,
                "locationType": location_type,
                "locationId": int(location_id),
                "parameterUrlInput": _glassdoor_parameter_url_input(
                    location=self.scraper_input.location or "",
                    location_id=location_id,
                    location_type=location_type,
                ),
                "pageNumber": page_num,
                "pageCursor": cursor,
                "fromage": fromage,
                "sort": "date",
            },
            "query": query_template,
        }
        return json.dumps([payload])

    return add_payload


def _glassdoor_parameter_url_input(
    location: str,
    location_id: int,
    location_type: str,
) -> str:
    location_text = location.strip()
    location_type_code = _glassdoor_location_type_code(location_type)
    return f"IL.0,{len(location_text)}_I{location_type_code}{location_id}"


def _glassdoor_location_type_code(location_type: str) -> str:
    if location_type == "CITY":
        return "C"
    if location_type == "STATE":
        return "S"
    if location_type == "COUNTRY":
        return "N"
    return location_type


def _glassdoor_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _glassdoor_location_type(value: str) -> str:
    if value == "C":
        return "CITY"
    if value == "S":
        return "STATE"
    if value == "N":
        return "COUNTRY"
    return value


def _glassdoor_location_fallback(
    glassdoor_scraper: Any,
    location: str,
) -> tuple[int, str] | None:
    country_name = _glassdoor_country_name(glassdoor_scraper)
    return GLASSDOOR_LOCATION_FALLBACKS.get(
        (country_name.casefold(), location.strip().casefold())
    )


def _glassdoor_country_name(glassdoor_scraper: Any) -> str:
    country = getattr(getattr(glassdoor_scraper, "scraper_input", None), "country", None)
    if country is None:
        return ""

    country_names = getattr(country, "value", [""])
    if country_names:
        return str(country_names[0]).split(",", maxsplit=1)[0]
    return str(getattr(country, "name", ""))


def _parse_jobspy_records(
    raw_jobs: Any,
    default_source: str | None = None,
) -> list[JobPosting]:
    records = _records_from_jobspy_result(raw_jobs)
    return [_job_from_record(record, default_source) for record in records]


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


def _job_from_record(
    record: dict[str, Any],
    default_source: str | None = None,
) -> JobPosting:
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
        source=_source_from_record(record, url, default_source),
        description=_clean_description(_string_value(record, "description") or ""),
        work_mode=(
            _string_value(record, "work_mode")
            or _string_value(record, "job_type")
            or _string_value(record, "interval")
        ),
        language=None,
        url=url,
    )


def _default_source(platforms: list[str]) -> str | None:
    if len(platforms) == 1:
        return platforms[0]
    return None


def _source_from_record(
    record: dict[str, Any],
    url: str | None,
    default_source: str | None,
) -> str:
    source = (
        _string_value(record, "site")
        or _string_value(record, "site_name")
        or _string_value(record, "source")
    )
    if source:
        return source.casefold()

    url_source = _source_from_url(url or "")
    if url_source:
        return url_source

    return default_source or "jobspy"


def _source_from_url(url: str) -> str | None:
    normalized_url = url.casefold()
    if "glassdoor." in normalized_url:
        return "glassdoor"
    if "linkedin." in normalized_url:
        return "linkedin"
    return None


def _string_value(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None

    string_value = str(value).strip()
    return string_value or None


def _clean_description(description: str) -> str:
    return re.sub(r"\s+", " ", description).strip()


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
