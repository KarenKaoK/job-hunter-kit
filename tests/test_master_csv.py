import csv

from job_hunter_kit.master_csv import (
    description_hash,
    load_master_jobs,
    master_job_id,
    merge_master_jobs,
    save_master_jobs,
)
from job_hunter_kit.models import FilterResult, JobPosting, MasterJobRow


def test_master_job_id_uses_job_id_when_available():
    job = _job(id="12345", url=None)

    assert master_job_id(job) == "linkedin:12345"


def test_master_job_id_uses_linkedin_url_id_before_job_id():
    job = _job(id="internal-id", url="https://www.linkedin.com/jobs/view/98765/")

    assert master_job_id(job) == "linkedin:98765"


def test_master_job_id_falls_back_to_readable_identity():
    job = _job(id="", url=None)

    assert master_job_id(job) == "linkedin:data-scientist-example-ag-berlin-germany"


def test_load_master_jobs_returns_empty_list_for_missing_file(tmp_path):
    assert load_master_jobs(tmp_path / "missing.csv") == []


def test_save_and_load_master_jobs_preserves_editable_fields(tmp_path):
    output_path = tmp_path / "linkedin_jobs.csv"
    row = _master_row(status="applied", notes="Applied on company site.")

    save_master_jobs(output_path, [row])
    loaded_rows = load_master_jobs(output_path)

    assert loaded_rows == [row]


def test_merge_master_jobs_adds_only_included_new_jobs():
    included = _filter_result(_job(id="include-001"), decision="include")
    excluded = _filter_result(_job(id="exclude-001"), decision="exclude")

    update = merge_master_jobs(
        [],
        [included, excluded],
        collected_at="2026-05-20T08:00:00+00:00",
        translation_enabled=False,
        translation_provider="google",
        translation_target_language="zh-CN",
        translation_timeout_seconds=15,
        translate_func=_fake_translate,
    )

    assert len(update.rows) == 1
    assert update.rows[0].status == "new"
    assert update.rows[0].job_id == "linkedin:include-001"
    assert update.rows[0].first_collected_at == "2026-05-20T08:00:00+00:00"
    assert update.rows[0].last_collected_at == "2026-05-20T08:00:00+00:00"
    assert update.collected_count == 2
    assert update.included_count == 1
    assert update.translated_count == 0


def test_merge_master_jobs_marks_existing_new_job_as_seen():
    existing = _master_row(status="new")
    result = _filter_result(
        _job(id="job-001", title="Updated Data Scientist"),
        decision="include",
    )

    update = merge_master_jobs(
        [existing],
        [result],
        collected_at="2026-05-20T08:00:00+00:00",
        translation_enabled=False,
        translation_provider="google",
        translation_target_language="zh-CN",
        translation_timeout_seconds=15,
        translate_func=_fake_translate,
    )

    assert update.rows[0].status == "seen"
    assert update.rows[0].first_collected_at == "2026-05-19T08:00:00+00:00"
    assert update.rows[0].last_collected_at == "2026-05-20T08:00:00+00:00"
    assert update.rows[0].title == "Updated Data Scientist"


def test_merge_master_jobs_preserves_applied_status_notes_and_historical_rows():
    applied = _master_row(status="applied", notes="Applied yesterday.")
    historical = _master_row(
        job_id="linkedin:historical",
        title="Historical Role",
        status="seen",
    )
    result = _filter_result(_job(id="job-001"), decision="include")

    update = merge_master_jobs(
        [applied, historical],
        [result],
        collected_at="2026-05-20T08:00:00+00:00",
        translation_enabled=False,
        translation_provider="google",
        translation_target_language="zh-CN",
        translation_timeout_seconds=15,
        translate_func=_fake_translate,
    )

    rows_by_id = {row.job_id: row for row in update.rows}
    assert rows_by_id["linkedin:job-001"].status == "applied"
    assert rows_by_id["linkedin:job-001"].notes == "Applied yesterday."
    assert rows_by_id["linkedin:job-001"].first_collected_at == "2026-05-19T08:00:00+00:00"
    assert rows_by_id["linkedin:job-001"].last_collected_at == "2026-05-20T08:00:00+00:00"
    assert rows_by_id["linkedin:historical"].title == "Historical Role"
    assert rows_by_id["linkedin:historical"].last_collected_at == "2026-05-19T08:00:00+00:00"


def test_save_master_jobs_writes_simplified_columns(tmp_path):
    output_path = tmp_path / "linkedin_jobs.csv"
    save_master_jobs(output_path, [_master_row()])

    with output_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert reader.fieldnames == [
        "status",
        "job_id",
        "first_collected_at",
        "last_collected_at",
        "title",
        "company",
        "location",
        "work_mode",
        "language",
        "source",
        "url",
        "description",
        "description_zh",
        "description_hash",
        "notes",
    ]
    assert rows[0]["job_id"] == "linkedin:job-001"
    assert "decision" not in rows[0]
    assert "matched_include_rules" not in rows[0]


def test_merge_master_jobs_translates_new_and_changed_descriptions():
    existing = _master_row(
        description="Old description",
        description_zh="旧描述",
        description_hash=description_hash("Old description"),
    )
    changed = _filter_result(_job(id="job-001", description="New description"), "include")

    update = merge_master_jobs(
        [existing],
        [changed],
        collected_at="2026-05-20T08:00:00+00:00",
        translation_enabled=True,
        translation_provider="google",
        translation_target_language="zh-CN",
        translation_timeout_seconds=15,
        translate_func=_fake_translate,
    )

    assert update.translated_count == 1
    assert update.reused_translation_count == 0
    assert update.translation_failed_count == 0
    assert update.rows[0].description_zh == "ZH:New description"


def test_merge_master_jobs_reuses_existing_translation_when_description_unchanged():
    existing = _master_row(
        description="Same description",
        description_zh="中文描述",
        description_hash=description_hash("Same description"),
    )
    same = _filter_result(_job(id="job-001", description="Same description"), "include")

    update = merge_master_jobs(
        [existing],
        [same],
        collected_at="2026-05-20T08:00:00+00:00",
        translation_enabled=True,
        translation_provider="google",
        translation_target_language="zh-CN",
        translation_timeout_seconds=15,
        translate_func=_translate_should_not_be_called,
    )

    assert update.translated_count == 0
    assert update.reused_translation_count == 1
    assert update.translation_failed_count == 0
    assert update.rows[0].description_zh == "中文描述"


def _job(
    id: str = "job-001",
    title: str = "Data Scientist",
    company: str = "Example AG",
    location: str = "Berlin, Germany",
    source: str = "linkedin",
    description: str = "Analyze product data.",
    work_mode: str | None = "remote",
    language: str | None = "English",
    url: str | None = None,
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


def _filter_result(job: JobPosting, decision: str) -> FilterResult:
    return FilterResult(
        job=job,
        decision=decision,
        matched_include_rules=[],
        matched_exclude_rules=[],
        reasons=[],
    )


def _master_row(
    job_id: str = "linkedin:job-001",
    title: str = "Data Scientist",
    status: str = "seen",
    description: str = "Analyze product data.",
    description_zh: str = "",
    description_hash: str = "",
    notes: str = "",
) -> MasterJobRow:
    return MasterJobRow(
        status=status,
        job_id=job_id,
        first_collected_at="2026-05-19T08:00:00+00:00",
        last_collected_at="2026-05-19T08:00:00+00:00",
        title=title,
        company="Example AG",
        location="Berlin, Germany",
        work_mode="remote",
        language="English",
        source="linkedin",
        url="",
        description=description,
        description_zh=description_zh,
        description_hash=description_hash,
        notes=notes,
    )


def _fake_translate(
    text: str,
    provider: str,
    target_language: str,
    timeout_seconds: int,
) -> str:
    return f"ZH:{text}"


def _translate_should_not_be_called(
    text: str,
    provider: str,
    target_language: str,
    timeout_seconds: int,
) -> str:
    raise AssertionError("translate function should not be called")
