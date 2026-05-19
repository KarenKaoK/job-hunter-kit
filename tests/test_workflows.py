import csv

from job_hunter_kit.models import CollectionConfig, FilterRuleConfig, SearchConfig
from job_hunter_kit.workflows import (
    collect_and_filter_jobs,
    collect_filter_track_and_save_csv,
    collect_filter_merge_master_csv,
)


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


def test_collect_filter_track_and_save_csv_tracks_new_seen_and_applied_jobs(tmp_path):
    config_path = tmp_path / "config.yaml"
    output_path = tmp_path / "jobs.csv"
    state_path = tmp_path / "job_state.csv"
    config_path.write_text(
        """
collection:
  search_terms:
    - data scientist
include:
  title_keywords:
    - data scientist
sources:
  - linkedin
""".strip(),
        encoding="utf-8",
    )
    state_path.write_text(
        "\n".join(
            [
                "job_key,status,first_seen_at,last_seen_at,title,company,location,source,url,notes",
                "url:https://linkedin.com/jobs/view/include-001,applied,2026-05-18T10:00:00+00:00,2026-05-18T10:00:00+00:00,Data Scientist,Example AG,Berlin Germany,linkedin,https://linkedin.com/jobs/view/include-001,Applied already",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_scrape_jobs(**kwargs):
        return FakeJobSpyFrame()

    results = collect_filter_track_and_save_csv(
        config_path,
        output_path,
        state_path,
        scrape_jobs_func=fake_scrape_jobs,
        seen_at="2026-05-19T10:00:00+00:00",
    )

    assert [result.status for result in results] == ["applied", "new"]
    assert [result.first_collected_at for result in results] == [
        "2026-05-18T10:00:00+00:00",
        "2026-05-19T10:00:00+00:00",
    ]
    assert [result.last_collected_at for result in results] == [
        "2026-05-19T10:00:00+00:00",
        "2026-05-19T10:00:00+00:00",
    ]

    with output_path.open("r", encoding="utf-8", newline="") as file:
        output_rows = list(csv.DictReader(file))
    assert [row["status"] for row in output_rows] == ["applied", "new"]
    assert [row["first_collected_at"] for row in output_rows] == [
        "2026-05-18T10:00:00+00:00",
        "2026-05-19T10:00:00+00:00",
    ]
    assert [row["last_collected_at"] for row in output_rows] == [
        "2026-05-19T10:00:00+00:00",
        "2026-05-19T10:00:00+00:00",
    ]

    with state_path.open("r", encoding="utf-8", newline="") as file:
        state_rows = list(csv.DictReader(file))
    state_by_key = {row["job_key"]: row for row in state_rows}
    assert state_by_key["url:https://linkedin.com/jobs/view/include-001"]["status"] == "applied"
    assert state_by_key["url:https://linkedin.com/jobs/view/include-001"]["first_seen_at"] == "2026-05-18T10:00:00+00:00"
    assert state_by_key["url:https://linkedin.com/jobs/view/include-001"]["last_seen_at"] == "2026-05-19T10:00:00+00:00"
    assert state_by_key["url:https://linkedin.com/jobs/view/include-001"]["notes"] == "Applied already"
    assert state_by_key["url:https://linkedin.com/jobs/view/exclude-001"]["status"] == "seen"
    assert state_by_key["url:https://linkedin.com/jobs/view/exclude-001"]["first_seen_at"] == "2026-05-19T10:00:00+00:00"
    assert state_by_key["url:https://linkedin.com/jobs/view/exclude-001"]["last_seen_at"] == "2026-05-19T10:00:00+00:00"


def test_collect_filter_merge_master_csv_writes_one_editable_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    output_path = tmp_path / "linkedin_jobs.csv"
    config_path.write_text(
        """
collection:
  search_terms:
    - data scientist
include:
  title_keywords:
    - data scientist
""".strip(),
        encoding="utf-8",
    )
    output_path.write_text(
        "\n".join(
            [
                "status,job_id,first_collected_at,last_collected_at,title,company,location,work_mode,language,source,url,description,notes",
                "applied,linkedin:include-001,2026-05-18T10:00:00+00:00,2026-05-18T10:00:00+00:00,Data Scientist,Example AG,Berlin Germany,,English,linkedin,https://linkedin.com/jobs/view/include-001,Old description,Applied already",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_scrape_jobs(**kwargs):
        return FakeJobSpyFrame()

    update = collect_filter_merge_master_csv(
        config_path,
        output_path,
        scrape_jobs_func=fake_scrape_jobs,
        collected_at="2026-05-20T10:00:00+00:00",
    )

    assert update.collected_count == 2
    assert update.included_count == 1
    assert update.applied_count == 1

    with output_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert rows[0]["status"] == "applied"
    assert rows[0]["job_id"] == "linkedin:include-001"
    assert rows[0]["first_collected_at"] == "2026-05-18T10:00:00+00:00"
    assert rows[0]["last_collected_at"] == "2026-05-20T10:00:00+00:00"
    assert rows[0]["description"] == "Analyze product data with Python."
    assert rows[0]["notes"] == "Applied already"
    assert "decision" not in rows[0]
