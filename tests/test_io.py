import csv

from job_hunter_kit.io import save_filter_results_csv
from job_hunter_kit.models import FilterResult, JobPosting


def test_save_filter_results_csv_writes_expected_columns(tmp_path):
    output_path = tmp_path / "jobs.csv"
    result = FilterResult(
        job=JobPosting(
            id="job-001",
            title="Data Scientist",
            company="Example AG",
            location="Berlin, Germany",
            source="linkedin",
            description="Analyze product data with Python.",
            work_mode="remote",
            language="English",
            url="https://linkedin.com/jobs/view/001",
        ),
        decision="include",
        matched_include_rules=["include.title_keywords:data scientist"],
        matched_exclude_rules=[],
        reasons=["Matched include rule and no exclude rules."],
    )

    save_filter_results_csv(output_path, [result])

    with output_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "decision": "include",
            "title": "Data Scientist",
            "company": "Example AG",
            "location": "Berlin, Germany",
            "work_mode": "remote",
            "language": "English",
            "source": "linkedin",
            "url": "https://linkedin.com/jobs/view/001",
            "matched_include_rules": "include.title_keywords:data scientist",
            "matched_exclude_rules": "",
            "reasons": "Matched include rule and no exclude rules.",
            "has_description": "true",
            "description_length": "33",
            "description": "Analyze product data with Python.",
        }
    ]
