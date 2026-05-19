from job_hunter_kit.models import FilterResult, JobPosting, JobStateEntry
from job_hunter_kit.state import (
    apply_job_state,
    job_key,
    load_job_state,
    save_job_state,
    update_job_state,
)


def test_job_key_prefers_url():
    job = _job(id="123", url="https://linkedin.com/jobs/view/123")

    assert job_key(job) == "url:https://linkedin.com/jobs/view/123"


def test_job_key_falls_back_to_source_and_id():
    job = _job(id="123", url=None)

    assert job_key(job) == "id:linkedin:123"


def test_job_key_falls_back_to_job_identity_when_id_is_missing():
    job = _job(id="", url=None)

    assert job_key(job) == "job:linkedin|data scientist|example ag|berlin, germany"


def test_load_job_state_returns_empty_dict_for_missing_file(tmp_path):
    state = load_job_state(tmp_path / "missing.csv")

    assert state == {}


def test_save_and_load_job_state_preserves_applied_status_and_notes(tmp_path):
    state_path = tmp_path / "job_state.csv"
    entry = JobStateEntry(
        job_key="url:https://linkedin.com/jobs/view/123",
        status="applied",
        first_seen_at="2026-05-18T10:00:00+00:00",
        last_seen_at="2026-05-19T10:00:00+00:00",
        title="Data Scientist",
        company="Example AG",
        location="Berlin, Germany",
        source="linkedin",
        url="https://linkedin.com/jobs/view/123",
        notes="Applied on company site.",
    )

    save_job_state(state_path, {entry.job_key: entry})
    loaded_state = load_job_state(state_path)

    assert loaded_state == {entry.job_key: entry}


def test_apply_job_state_marks_new_seen_and_applied_jobs():
    new_result = _filter_result(_job(id="new", url="https://linkedin.com/jobs/new"))
    seen_result = _filter_result(_job(id="seen", url="https://linkedin.com/jobs/seen"))
    applied_result = _filter_result(
        _job(id="applied", url="https://linkedin.com/jobs/applied")
    )
    state = {
        job_key(seen_result.job): _state_entry(seen_result.job, status="seen"),
        job_key(applied_result.job): _state_entry(applied_result.job, status="applied"),
    }

    run_results = apply_job_state(
        [new_result, seen_result, applied_result],
        state,
        seen_at="2026-05-19T10:00:00+00:00",
    )

    assert [result.status for result in run_results] == ["new", "seen", "applied"]
    assert [result.first_collected_at for result in run_results] == [
        "2026-05-19T10:00:00+00:00",
        "2026-05-18T10:00:00+00:00",
        "2026-05-18T10:00:00+00:00",
    ]
    assert [result.last_collected_at for result in run_results] == [
        "2026-05-19T10:00:00+00:00",
        "2026-05-19T10:00:00+00:00",
        "2026-05-19T10:00:00+00:00",
    ]


def test_update_job_state_saves_new_jobs_as_seen_and_preserves_notes():
    existing_job = _job(id="existing", url="https://linkedin.com/jobs/existing")
    new_job = _job(id="new", url="https://linkedin.com/jobs/new")
    existing_entry = _state_entry(
        existing_job,
        status="applied",
        notes="Already applied.",
    )
    state = {job_key(existing_job): existing_entry}
    run_results = apply_job_state(
        [_filter_result(existing_job), _filter_result(new_job)],
        state,
        seen_at="2026-05-19T10:00:00+00:00",
    )

    updated_state = update_job_state(
        run_results,
        state,
        seen_at="2026-05-19T10:00:00+00:00",
    )

    assert updated_state[job_key(existing_job)].status == "applied"
    assert updated_state[job_key(existing_job)].first_seen_at == "2026-05-18T10:00:00+00:00"
    assert updated_state[job_key(existing_job)].notes == "Already applied."
    assert updated_state[job_key(existing_job)].last_seen_at == "2026-05-19T10:00:00+00:00"
    assert updated_state[job_key(new_job)].status == "seen"
    assert updated_state[job_key(new_job)].first_seen_at == "2026-05-19T10:00:00+00:00"


def _job(
    id: str = "job-001",
    title: str = "Data Scientist",
    company: str = "Example AG",
    location: str = "Berlin, Germany",
    source: str = "linkedin",
    description: str = "Analyze product data.",
    url: str | None = "https://linkedin.com/jobs/view/001",
) -> JobPosting:
    return JobPosting(
        id=id,
        title=title,
        company=company,
        location=location,
        source=source,
        description=description,
        url=url,
    )


def _filter_result(job: JobPosting) -> FilterResult:
    return FilterResult(
        job=job,
        decision="include",
        matched_include_rules=[],
        matched_exclude_rules=[],
        reasons=[],
    )


def _state_entry(
    job: JobPosting,
    status: str = "seen",
    notes: str = "",
) -> JobStateEntry:
    return JobStateEntry(
        job_key=job_key(job),
        status=status,
        first_seen_at="2026-05-18T10:00:00+00:00",
        last_seen_at="2026-05-18T10:00:00+00:00",
        title=job.title,
        company=job.company,
        location=job.location,
        source=job.source,
        url=job.url or "",
        notes=notes,
    )
