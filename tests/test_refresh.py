import csv

from job_hunter_kit.refresh import append_new_analyzed_jobs, export_new_jobs_to_analyze


def test_export_new_jobs_to_analyze_uses_job_id_then_url_and_exports_only_new(tmp_path):
    crawl_path = tmp_path / "linkedin_jobs.csv"
    analyzed_path = tmp_path / "analyzed_jobs.csv"
    output_path = tmp_path / "new_jobs_to_analyze.csv"

    _write_csv(
        crawl_path,
        [
            {
                "job_id": "linkedin:1",
                "title": "A",
                "company": "CompA",
                "location": "Berlin",
                "url": "https://example.com/1",
                "description": "desc1",
                "description_hash": "h1",
                "source": "linkedin",
                "last_collected_at": "2026-05-21T00:00:00+00:00",
            },
            {
                "job_id": "",
                "title": "B",
                "company": "CompB",
                "location": "Munich",
                "url": "https://example.com/2",
                "description": "desc2",
                "description_hash": "h2",
                "source": "linkedin",
                "collected_at": "2026-05-21T01:00:00+00:00",
            },
            {
                "job_id": "",
                "title": "Invalid",
                "company": "NoKey",
                "location": "",
                "url": "",
                "description": "",
            },
        ],
    )
    _write_csv(
        analyzed_path,
        [
            {
                "job_id": "linkedin:1",
                "url": "https://example.com/should-not-be-used",
                "application_status": "Applied",
            }
        ],
    )

    summary = export_new_jobs_to_analyze(crawl_path, analyzed_path, output_path)
    rows = _read_csv(output_path)

    assert summary["crawled_total"] == 3
    assert summary["analyzed_total"] == 1
    assert summary["new_exported"] == 1
    assert summary["crawled_invalid_key_rows"] == 1
    assert len(rows) == 1
    assert rows[0]["title"] == "B"
    assert rows[0]["url"] == "https://example.com/2"
    assert rows[0]["collected_at"] == "2026-05-21T01:00:00+00:00"


def test_append_new_analyzed_jobs_appends_only_new_and_preserves_existing(tmp_path):
    analyzed_path = tmp_path / "analyzed_jobs.csv"
    new_analyzed_path = tmp_path / "new_analyzed_jobs.csv"

    _write_csv(
        analyzed_path,
        [
            {
                "job_id": "linkedin:1",
                "url": "https://example.com/1",
                "title": "Existing",
                "application_status": "Applied",
                "applied_date": "2026-05-20",
                "notes": "done",
                "status_updated_at": "2026-05-20T10:00:00+00:00",
                "match_score": "80",
            }
        ],
    )
    _write_csv(
        new_analyzed_path,
        [
            {
                "job_id": "linkedin:1",
                "url": "https://example.com/1",
                "title": "Duplicate should skip",
                "match_score": "10",
            },
            {
                "job_id": "",
                "url": "https://example.com/2",
                "title": "New by url",
                "match_score": "90",
            },
            {
                "job_id": "",
                "url": "",
                "title": "Invalid",
            },
        ],
    )

    summary = append_new_analyzed_jobs(analyzed_path, new_analyzed_path)
    rows = _read_csv(analyzed_path)

    assert summary["existing_total_before"] == 1
    assert summary["new_analyzed_total"] == 3
    assert summary["appended"] == 1
    assert summary["duplicates_skipped"] == 1
    assert summary["new_invalid_key_rows"] == 1
    assert summary["final_total"] == 2

    existing_row = next(row for row in rows if row.get("job_id") == "linkedin:1")
    assert existing_row["title"] == "Existing"
    assert existing_row["application_status"] == "Applied"
    assert existing_row["applied_date"] == "2026-05-20"
    assert existing_row["notes"] == "done"
    assert existing_row["status_updated_at"] == "2026-05-20T10:00:00+00:00"

    new_row = next(row for row in rows if row.get("url") == "https://example.com/2")
    assert new_row["application_status"] == "Not Applied"
    assert new_row["applied_date"] == ""
    assert new_row["notes"] == ""
    assert new_row["status_updated_at"] == ""


def test_append_new_analyzed_jobs_creates_canonical_file_when_missing(tmp_path):
    analyzed_path = tmp_path / "analyzed_jobs.csv"
    new_analyzed_path = tmp_path / "new_analyzed_jobs.csv"

    _write_csv(
        new_analyzed_path,
        [
            {
                "job_id": "linkedin:100",
                "title": "First Row",
                "url": "https://example.com/100",
            }
        ],
    )

    summary = append_new_analyzed_jobs(analyzed_path, new_analyzed_path)
    rows = _read_csv(analyzed_path)

    assert summary["existing_total_before"] == 0
    assert summary["appended"] == 1
    assert len(rows) == 1
    assert rows[0]["application_status"] == "Not Applied"


def test_append_new_analyzed_jobs_supports_job_id_and_url_aliases(tmp_path):
    analyzed_path = tmp_path / "analyzed_jobs.csv"
    new_analyzed_path = tmp_path / "new_analyzed_jobs.csv"

    _write_csv(
        analyzed_path,
        [
            {
                "Job ID": "linkedin:1",
                "URL": "https://example.com/1",
                "application_status": "Applied",
            }
        ],
    )
    _write_csv(
        new_analyzed_path,
        [
            {
                "Job ID": "linkedin:1",
                "URL": "https://example.com/1",
                "Title": "Duplicate",
            },
            {
                "Job ID": "linkedin:2",
                "URL": "https://example.com/2",
                "Title": "New Row",
            },
        ],
    )

    summary = append_new_analyzed_jobs(analyzed_path, new_analyzed_path)
    rows = _read_csv(analyzed_path)

    assert summary["existing_invalid_key_rows"] == 0
    assert summary["new_invalid_key_rows"] == 0
    assert summary["duplicates_skipped"] == 1
    assert summary["appended"] == 1
    assert len(rows) == 2


def test_append_new_analyzed_jobs_supports_job_link_alias(tmp_path):
    analyzed_path = tmp_path / "analyzed_jobs.csv"
    new_analyzed_path = tmp_path / "new_analyzed_jobs.csv"

    _write_csv(
        analyzed_path,
        [
            {
                "Job ID": "linkedin:1",
                "URL": "https://example.com/1",
            }
        ],
    )
    _write_csv(
        new_analyzed_path,
        [
            {
                "Job ID": "",
                "Job Link": "https://example.com/3",
                "Title": "Link Only",
            }
        ],
    )

    summary = append_new_analyzed_jobs(analyzed_path, new_analyzed_path)
    rows = _read_csv(analyzed_path)

    assert summary["appended"] == 1
    assert len(rows) == 2

def _write_csv(path, rows):
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))
