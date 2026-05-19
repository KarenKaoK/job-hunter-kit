from job_hunter_kit.models import CollectionConfig, FilterRuleConfig, SearchConfig
from job_hunter_kit.workflows import collect_and_filter_jobs


class FakeJobSpyFrame:
    def to_dict(self, orient):
        assert orient == "records"
        return [
            {
                "id": "include-001",
                "title": "Data Scientist",
                "company": "Example AG",
                "location": "Berlin, Germany",
                "job_url": "https://linkedin.com/jobs/view/include-001",
                "description": "Analyze product data with Python.",
            },
            {
                "id": "exclude-001",
                "title": "Engineering Manager",
                "company": "Example GmbH",
                "location": "Berlin, Germany",
                "job_url": "https://linkedin.com/jobs/view/exclude-001",
                "description": "Manage engineering teams.",
            },
        ]


def test_collect_and_filter_jobs_uses_existing_filter_logic():
    def fake_scrape_jobs(**kwargs):
        return FakeJobSpyFrame()

    config = SearchConfig(
        collection=CollectionConfig(search_terms=["data scientist"]),
        include=FilterRuleConfig(title_keywords=["data scientist"]),
        exclude=FilterRuleConfig(title_keywords=["manager"]),
    )

    results = collect_and_filter_jobs(config, scrape_jobs_func=fake_scrape_jobs)

    assert [result.decision for result in results] == ["include", "exclude"]
    assert results[0].matched_include_rules == [
        "include.title_keywords:data scientist"
    ]
    assert results[1].matched_exclude_rules == ["exclude.title_keywords:manager"]
