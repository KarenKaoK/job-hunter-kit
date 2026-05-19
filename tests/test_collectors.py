from job_hunter_kit.collectors import collect_jobs
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
    assert [job.source for job in jobs] == ["linkedin", "linkedin"]


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
