from job_hunter_kit.filters import filter_job, filter_jobs, included_jobs
from job_hunter_kit.models import FilterRuleConfig, JobPosting, SearchConfig


def test_filter_job_includes_matching_title_keyword():
    job = _job(title="Machine Learning Engineer")
    config = SearchConfig(
        include=FilterRuleConfig(title_keywords=["machine learning"]),
    )

    result = filter_job(job, config)

    assert result.decision == "include"
    assert result.matched_include_rules == [
        "include.title_keywords:machine learning"
    ]
    assert result.matched_exclude_rules == []


def test_filter_job_excludes_when_no_include_rules_match():
    job = _job(title="Product Manager")
    config = SearchConfig(
        include=FilterRuleConfig(title_keywords=["data scientist"]),
    )

    result = filter_job(job, config)

    assert result.decision == "exclude"
    assert result.reasons == ["Did not match any include rule."]


def test_filter_job_exclude_rules_override_include_rules():
    job = _job(
        title="Data Scientist",
        description="This is an unpaid internship for data science.",
    )
    config = SearchConfig(
        include=FilterRuleConfig(title_keywords=["data scientist"]),
        exclude=FilterRuleConfig(keywords=["unpaid"]),
    )

    result = filter_job(job, config)

    assert result.decision == "exclude"
    assert result.matched_include_rules == [
        "include.title_keywords:data scientist"
    ]
    assert result.matched_exclude_rules == ["exclude.keywords:unpaid"]
    assert result.reasons == ["Matched exclude rule."]


def test_filter_job_matches_location_and_work_mode_case_insensitively():
    job = _job(location="Berlin, Germany", work_mode="Hybrid")
    config = SearchConfig(
        include=FilterRuleConfig(locations=["berlin"], work_modes=["hybrid"]),
    )

    result = filter_job(job, config)

    assert result.decision == "include"
    assert "include.locations:berlin" in result.matched_include_rules
    assert "include.work_modes:hybrid" in result.matched_include_rules


def test_filter_job_excludes_language_requirement_from_description():
    job = _job(
        title="AI Engineer",
        description="Native German communication is required.",
    )
    config = SearchConfig(
        include=FilterRuleConfig(title_keywords=["ai engineer"]),
        exclude=FilterRuleConfig(language_requirements=["native german"]),
    )

    result = filter_job(job, config)

    assert result.decision == "exclude"
    assert result.matched_exclude_rules == [
        "exclude.language_requirements:native german"
    ]


def test_included_jobs_returns_only_included_postings():
    included = _job(id="1", title="Data Scientist")
    excluded = _job(id="2", title="Engineering Manager")
    config = SearchConfig(
        include=FilterRuleConfig(title_keywords=["data scientist"]),
        exclude=FilterRuleConfig(title_keywords=["manager"]),
    )

    results = filter_jobs([included, excluded], config)
    jobs = included_jobs([included, excluded], config)

    assert [result.decision for result in results] == ["include", "exclude"]
    assert jobs == [included]


def _job(
    id: str = "sample-001",
    title: str = "Data Scientist",
    company: str = "Example GmbH",
    location: str = "Munich, Germany",
    source: str = "sample",
    description: str = "Build models with Python and communicate in English.",
    work_mode: str | None = "remote",
    language: str | None = "English",
    url: str | None = "https://example.com/jobs/sample-001",
) -> JobPosting:
    return JobPosting(
        id=id,
        title=title,
        company=company,
        location=location,
        source=source,
        description=description,
        work_mode=work_mode,
        language=language,
        url=url,
    )
