import json
import logging
from types import SimpleNamespace

import pytest

from job_hunter_kit.collectors import _patch_jobspy_glassdoor_scraper, collect_jobs
from job_hunter_kit.models import CollectionConfig


class FakeJobSpyFrame:
    def __init__(self, records):
        self.records = records

    def to_dict(self, orient):
        assert orient == "records"
        return self.records


def test_collect_jobs_calls_jobspy_for_each_search_term():
    calls = []

    def fake_scrape_jobs(**kwargs):
        calls.append(kwargs)
        return FakeJobSpyFrame(
            [
                {
                    "id": f"{kwargs['search_term']}-001",
                    "title": "Machine Learning Engineer",
                    "company": "Example GmbH",
                    "location": "Berlin, Germany",
                    "job_url": f"https://linkedin.com/jobs/{kwargs['search_term']}",
                    "description": "Build ML systems with Python.",
                }
            ]
        )

    config = CollectionConfig(
        search_terms=["machine learning engineer", "data scientist"],
        results_per_term=10,
        hours_old=24,
        linkedin_fetch_description=True,
    )

    jobs = collect_jobs(config, scrape_jobs_func=fake_scrape_jobs)

    assert [call["site_name"] for call in calls] == [["linkedin"], ["linkedin"]]
    assert [call["search_term"] for call in calls] == [
        "machine learning engineer",
        "data scientist",
    ]
    assert all(call["location"] == "Germany" for call in calls)
    assert all(call["results_wanted"] == 10 for call in calls)
    assert all(call["hours_old"] == 24 for call in calls)
    assert all(call["linkedin_fetch_description"] is True for call in calls)
    assert all("country_indeed" not in call for call in calls)
    assert [job.source for job in jobs] == ["linkedin", "linkedin"]


def test_collect_jobs_calls_jobspy_for_each_location_and_search_term():
    calls = []

    def fake_scrape_jobs(**kwargs):
        calls.append(kwargs)
        return FakeJobSpyFrame(
            [
                {
                    "id": f"{kwargs['location']}-{kwargs['search_term']}",
                    "title": "Data Scientist",
                    "company": "Example AG",
                    "location": kwargs["location"],
                    "job_url": (
                        "https://linkedin.com/jobs/"
                        f"{kwargs['location']}-{kwargs['search_term']}"
                    ),
                    "description": "Analyze data with Python.",
                }
            ]
        )

    config = CollectionConfig(
        locations=["Berlin", "Munich", "Europe", "Netherlands"],
        search_terms=["data scientist", "ai engineer"],
    )

    jobs = collect_jobs(config, scrape_jobs_func=fake_scrape_jobs)

    assert [
        (call["location"], call["search_term"])
        for call in calls
    ] == [
        ("Berlin", "data scientist"),
        ("Berlin", "ai engineer"),
        ("Munich", "data scientist"),
        ("Munich", "ai engineer"),
        ("Europe", "data scientist"),
        ("Europe", "ai engineer"),
        ("Netherlands", "data scientist"),
        ("Netherlands", "ai engineer"),
    ]
    assert len(jobs) == 8


def test_collect_jobs_converts_jobspy_rows_to_job_postings():
    def fake_scrape_jobs(**kwargs):
        return FakeJobSpyFrame(
            [
                {
                    "job_id": "linkedin-123",
                    "title": "Data Scientist",
                    "company_name": "Example Analytics AG",
                    "location": "Munich, Germany",
                    "job_url": "https://linkedin.com/jobs/view/123",
                    "description": "Analyze data with Python.",
                    "job_type": "remote",
                }
            ]
        )

    jobs = collect_jobs(
        CollectionConfig(search_terms=["data scientist"]),
        scrape_jobs_func=fake_scrape_jobs,
    )

    assert len(jobs) == 1
    assert jobs[0].id == "linkedin-123"
    assert jobs[0].title == "Data Scientist"
    assert jobs[0].company == "Example Analytics AG"
    assert jobs[0].location == "Munich, Germany"
    assert jobs[0].source == "linkedin"
    assert jobs[0].description == "Analyze data with Python."
    assert jobs[0].work_mode == "remote"
    assert jobs[0].url == "https://linkedin.com/jobs/view/123"


def test_collect_jobs_passes_country_indeed_for_glassdoor():
    calls = []

    def fake_scrape_jobs(**kwargs):
        calls.append(kwargs)
        return FakeJobSpyFrame(
            [
                {
                    "id": "glassdoor-123",
                    "site": "glassdoor",
                    "title": "ML Engineer",
                    "company": "Example Labs",
                    "location": "Berlin, Germany",
                    "job_url": "https://www.glassdoor.com/job-listing/ml-engineer.htm?jl=1001",
                    "description": "Build ML products.",
                }
            ]
        )

    config = CollectionConfig(
        platforms=["glassdoor"],
        search_terms=["machine learning engineer"],
        country_indeed="Germany",
    )

    jobs = collect_jobs(config, scrape_jobs_func=fake_scrape_jobs)

    assert calls[0]["site_name"] == ["glassdoor"]
    assert calls[0]["country_indeed"] == "Germany"
    assert "linkedin_fetch_description" not in calls[0]
    assert jobs[0].source == "glassdoor"


def test_collect_jobs_calls_jobspy_separately_for_each_platform():
    calls = []

    def fake_scrape_jobs(**kwargs):
        calls.append(kwargs)
        platform = kwargs["site_name"][0]
        return FakeJobSpyFrame(
            [
                {
                    "id": f"{platform}-123",
                    "site": platform,
                    "title": "ML Engineer",
                    "company": "Example Labs",
                    "location": kwargs["location"],
                    "job_url": f"https://www.{platform}.com/jobs/view/{platform}-123",
                    "description": "Build ML systems.",
                }
            ]
        )

    config = CollectionConfig(
        platforms=["linkedin", "glassdoor"],
        locations=["Berlin"],
        search_terms=["machine learning engineer"],
        country_indeed="Germany",
        linkedin_fetch_description=True,
    )

    jobs = collect_jobs(config, scrape_jobs_func=fake_scrape_jobs)

    assert [call["site_name"] for call in calls] == [["linkedin"], ["glassdoor"]]
    assert calls[0]["linkedin_fetch_description"] is True
    assert "country_indeed" not in calls[0]
    assert calls[1]["country_indeed"] == "Germany"
    assert "linkedin_fetch_description" not in calls[1]
    assert [job.source for job in jobs] == ["linkedin", "glassdoor"]


def test_collect_jobs_keeps_other_platform_results_when_one_platform_fails():
    def fake_scrape_jobs(**kwargs):
        platform = kwargs["site_name"][0]
        if platform == "glassdoor":
            raise RuntimeError("location not parsed")
        return FakeJobSpyFrame(
            [
                {
                    "id": "linkedin-123",
                    "site": "linkedin",
                    "title": "Data Scientist",
                    "company": "Example AG",
                    "location": "Berlin",
                    "job_url": "https://linkedin.com/jobs/view/123",
                    "description": "Analyze data.",
                }
            ]
        )

    config = CollectionConfig(
        platforms=["linkedin", "glassdoor"],
        locations=["Berlin"],
        search_terms=["data scientist"],
    )

    with pytest.warns(RuntimeWarning, match="JobSpy glassdoor collection failed"):
        jobs = collect_jobs(config, scrape_jobs_func=fake_scrape_jobs)

    assert len(jobs) == 1
    assert jobs[0].source == "linkedin"


def test_collect_jobs_infers_source_from_glassdoor_url():
    def fake_scrape_jobs(**kwargs):
        return FakeJobSpyFrame(
            [
                {
                    "id": "1001",
                    "title": "ML Engineer",
                    "company": "Example Labs",
                    "location": "Berlin, Germany",
                    "job_url": "https://www.glassdoor.com/job-listing/ml-engineer.htm?jl=1001",
                    "description": "Build ML products.",
                }
            ]
        )

    jobs = collect_jobs(
        CollectionConfig(
            platforms=["linkedin", "glassdoor"],
            search_terms=["machine learning engineer"],
        ),
        scrape_jobs_func=fake_scrape_jobs,
    )

    assert jobs[0].source == "glassdoor"


def test_collect_jobs_cleans_description_whitespace():
    def fake_scrape_jobs(**kwargs):
        return FakeJobSpyFrame(
            [
                {
                    "id": "linkedin-123",
                    "title": "Data Scientist",
                    "company": "Example Analytics AG",
                    "location": "Munich, Germany",
                    "job_url": "https://linkedin.com/jobs/view/123",
                    "description": (
                        "Analyze data\n\n\n"
                        "with Python.\t\tBuild dashboards.\n"
                        "   Communicate results."
                    ),
                }
            ]
        )

    jobs = collect_jobs(
        CollectionConfig(search_terms=["data scientist"]),
        scrape_jobs_func=fake_scrape_jobs,
    )

    assert (
        jobs[0].description
        == "Analyze data with Python. Build dashboards. Communicate results."
    )


def test_collect_jobs_deduplicates_by_url():
    def fake_scrape_jobs(**kwargs):
        return FakeJobSpyFrame(
            [
                {
                    "id": kwargs["search_term"],
                    "title": "AI Engineer",
                    "company": "Example Health GmbH",
                    "location": "Hamburg, Germany",
                    "job_url": "https://linkedin.com/jobs/view/duplicate",
                    "description": "Develop AI features.",
                }
            ]
        )

    jobs = collect_jobs(
        CollectionConfig(search_terms=["ai engineer", "machine learning engineer"]),
        scrape_jobs_func=fake_scrape_jobs,
    )

    assert len(jobs) == 1
    assert jobs[0].url == "https://linkedin.com/jobs/view/duplicate"


def test_collect_jobs_returns_empty_list_without_search_terms():
    jobs = collect_jobs(CollectionConfig(), scrape_jobs_func=lambda **kwargs: [])

    assert jobs == []


def test_patch_jobspy_glassdoor_scraper_fetches_csrf_from_homepage_idempotently():
    class FakeGlassdoor:
        pass

    session = FakeSession(status_code=200, text='{"token": "csrf-token"}')
    scraper = SimpleNamespace(session=session, base_url="https://www.glassdoor.de/")

    _patch_jobspy_glassdoor_scraper(FakeGlassdoor)
    _patch_jobspy_glassdoor_scraper(FakeGlassdoor)

    assert FakeGlassdoor._get_csrf_token(scraper) == "csrf-token"
    assert session.requested_urls == ["https://www.glassdoor.de/"]


def test_patch_jobspy_glassdoor_scraper_uses_known_location_fallback(caplog):
    class FakeGlassdoor:
        pass

    session = FakeSession(status_code=404, text="not found")
    scraper = SimpleNamespace(
        session=session,
        base_url="https://www.glassdoor.de/",
        scraper_input=SimpleNamespace(
            country=SimpleNamespace(value=("germany", "de", "de"))
        ),
    )

    _patch_jobspy_glassdoor_scraper(FakeGlassdoor)

    with caplog.at_level(logging.INFO, logger="job_hunter_kit.collectors"):
        location_id, location_type = FakeGlassdoor._get_location(
            scraper,
            "Berlin",
            False,
        )

    assert (location_id, location_type) == (2622109, "CITY")
    assert "using configured location fallback" in caplog.text
    assert session.requested_urls == [
        "https://www.glassdoor.de/findPopularLocationAjax.htm?maxLocationsToReturn=10&term=Berlin"
    ]


def test_patch_jobspy_glassdoor_scraper_uses_lookup_result_when_available():
    class FakeGlassdoor:
        pass

    session = FakeSession(
        status_code=200,
        json_data=[{"locationId": "4990924", "locationType": "C"}],
    )
    scraper = SimpleNamespace(session=session, base_url="https://www.glassdoor.de")

    _patch_jobspy_glassdoor_scraper(FakeGlassdoor)

    assert FakeGlassdoor._get_location(scraper, "Munich", False) == (4990924, "CITY")


def test_patch_jobspy_glassdoor_scraper_uses_compact_location_parameter():
    class FakeGlassdoor:
        pass

    scraper = SimpleNamespace(
        scraper_input=SimpleNamespace(
            hours_old=72,
            easy_apply=False,
            job_type=None,
            search_term="machine learning engineer",
            location="Berlin",
        )
    )

    _patch_jobspy_glassdoor_scraper(FakeGlassdoor, "query JobSearchResultsQuery")

    payload = json.loads(
        FakeGlassdoor._add_payload(scraper, 2622109, "CITY", 1)
    )[0]

    assert payload["variables"]["locationType"] == "CITY"
    assert payload["variables"]["locationId"] == 2622109
    assert payload["variables"]["parameterUrlInput"] == "IL.0,6_IC2622109"
    assert payload["variables"]["filterParams"] == [
        {"filterKey": "fromAge", "values": "3"}
    ]


def test_patch_jobspy_glassdoor_scraper_warns_with_response_diagnostics():
    class FakeGlassdoor:
        pass

    session = FakeSession(
        status_code=400,
        text="<html>Bad GraphQL request</html>",
    )
    scraper = FakeGlassdoor()
    scraper.session = session
    scraper.base_url = "https://www.glassdoor.de/"
    scraper.scraper_input = SimpleNamespace(
        hours_old=72,
        easy_apply=False,
        job_type=None,
        search_term="machine learning engineer",
        location="Berlin",
    )

    _patch_jobspy_glassdoor_scraper(FakeGlassdoor, "query JobSearchResultsQuery")

    with pytest.warns(RuntimeWarning) as warnings_record:
        jobs, cursor = FakeGlassdoor._fetch_jobs_page(
            scraper,
            scraper.scraper_input,
            2622109,
            "CITY",
            1,
            None,
        )

    assert jobs == []
    assert cursor is None
    message = str(warnings_record[0].message)
    assert "status=400" in message
    assert "location='Berlin'" in message
    assert "parameterUrlInput='IL.0,6_IC2622109'" in message
    assert "filterParams=[{'filterKey': 'fromAge', 'values': '3'}]" in message
    assert "Bad GraphQL request" in message
    assert session.posted_urls == ["https://www.glassdoor.de/graph"]


class FakeSession:
    def __init__(
        self,
        status_code: int,
        text: str = "",
        json_data=None,
    ):
        self.status_code = status_code
        self.text = text
        self.json_data = json_data or []
        self.requested_urls = []
        self.posted_urls = []

    def get(self, url):
        self.requested_urls.append(url)
        return self

    def post(self, url, **kwargs):
        self.posted_urls.append(url)
        self.post_kwargs = kwargs
        return self

    def json(self):
        return self.json_data
