from pathlib import Path

import pandas as pd
import pytest

from job_hunter_kit.dashboard_data import (
    COMPACT_LIST_FIELDS,
    DETAIL_READONLY_FIELDS,
    FIELD_ALIASES,
    DashboardPaths,
    apply_edits,
    compact_list_columns,
    filter_dataframe,
    load_or_bootstrap_dataframe,
    resolve_columns,
    selector_label,
    selected_row_index,
    sort_for_dashboard,
    update_selected_row,
    value_for_field,
)


def test_load_or_bootstrap_reads_csv_when_present(tmp_path):
    csv_path = tmp_path / "analyzed_jobs.csv"
    excel_path = tmp_path / "linked_jobs_analyzed.xlsx"
    pd.DataFrame(
        [
            {
                "title": "Data Scientist",
                "company": "Example AG",
                "application_status": "Applied",
                "applied_date": "2026-05-20",
                "notes": "Done",
            }
        ]
    ).to_csv(csv_path, index=False)

    df = load_or_bootstrap_dataframe(
        DashboardPaths(
            csv_path=csv_path,
            excel_path=excel_path,
            excel_sheet="job_ranking",
        )
    )

    assert len(df) == 1
    assert df.loc[0, "application_status"] == "Applied"


def test_load_or_bootstrap_keeps_deleted_status(tmp_path):
    csv_path = tmp_path / "analyzed_jobs.csv"
    excel_path = tmp_path / "linked_jobs_analyzed.xlsx"
    pd.DataFrame(
        [
            {
                "title": "Data Scientist",
                "company": "Example AG",
                "application_status": "Deleted",
                "applied_date": "",
                "notes": "not a fit",
            }
        ]
    ).to_csv(csv_path, index=False)

    df = load_or_bootstrap_dataframe(
        DashboardPaths(
            csv_path=csv_path,
            excel_path=excel_path,
            excel_sheet="job_ranking",
        )
    )

    assert df.loc[0, "application_status"] == "Deleted"


def test_load_or_bootstrap_reads_excel_when_csv_missing(tmp_path):
    pytest.importorskip("openpyxl")

    csv_path = tmp_path / "analyzed_jobs.csv"
    excel_path = tmp_path / "linked_jobs_analyzed.xlsx"
    pd.DataFrame(
        [
            {
                "title": "ML Engineer",
                "company": "Example GmbH",
                "application_status": "Not Applied",
            }
        ]
    ).to_excel(excel_path, sheet_name="job_ranking", index=False)

    df = load_or_bootstrap_dataframe(
        DashboardPaths(
            csv_path=csv_path,
            excel_path=excel_path,
            excel_sheet="job_ranking",
        )
    )

    assert len(df) == 1
    assert csv_path.exists()


def test_filter_dataframe_applies_keyword_priority_status_and_score():
    df = pd.DataFrame(
        [
            {
                "company": "Example AG",
                "title": "Data Scientist",
                "skills_required": "python, sql",
                "jd_summary": "build models",
                "priority": "High",
                "german_required": "No",
                "application_status": "Not Applied",
                "match_score": 88,
            },
            {
                "company": "Other GmbH",
                "title": "Backend Engineer",
                "skills_required": "go, k8s",
                "jd_summary": "backend systems",
                "priority": "Low",
                "german_required": "Yes",
                "application_status": "Applied",
                "match_score": 60,
            },
        ]
    )

    filtered = filter_dataframe(
        df=df,
        column_map=resolve_columns(df),
        keyword="data",
        priorities=["High"],
        german_required_values=["No"],
        application_status_values=["Not Applied"],
        min_match_score=80.0,
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["title"] == "Data Scientist"


def test_apply_edits_updates_only_editable_columns():
    original = pd.DataFrame(
        [
            {
                "title": "Data Scientist",
                "company": "Example AG",
                "application_status": "Not Applied",
                "applied_date": "",
                "notes": "",
                "match_score": 90,
            }
        ],
        index=[10],
    )
    edited_view = pd.DataFrame(
        [
            {
                "title": "CHANGED TITLE SHOULD NOT APPLY",
                "company": "CHANGED COMPANY SHOULD NOT APPLY",
                "application_status": "Applied",
                "applied_date": "2026-05-20",
                "notes": "applied via company site",
                "match_score": 10,
            }
        ],
        index=[10],
    )

    updated = apply_edits(original, edited_view)

    assert updated.loc[10, "application_status"] == "Applied"
    assert updated.loc[10, "applied_date"] == "2026-05-20"
    assert updated.loc[10, "notes"] == "applied via company site"
    assert updated.loc[10, "title"] == "Data Scientist"
    assert updated.loc[10, "company"] == "Example AG"
    assert updated.loc[10, "match_score"] == 90


def test_load_or_bootstrap_raises_when_no_csv_and_no_excel(tmp_path):
    paths = DashboardPaths(
        csv_path=tmp_path / "missing.csv",
        excel_path=tmp_path / "missing.xlsx",
        excel_sheet="job_ranking",
    )

    try:
        load_or_bootstrap_dataframe(paths)
    except FileNotFoundError:
        assert True
    else:
        assert False, "Expected FileNotFoundError"


def test_compact_list_columns_returns_only_expected_existing_columns():
    df = pd.DataFrame(
        [
            {
                "company": "Example AG",
                "title": "Data Scientist",
                "location": "Berlin",
                "match_score": 88,
                "application_status": "Not Applied",
                "random_col": "x",
            }
        ]
    )

    columns = compact_list_columns(df)

    assert columns == [
        "company",
        "title",
        "location",
        "match_score",
        "application_status",
    ]


def test_selected_row_index_uses_existing_or_falls_back_to_first():
    df = pd.DataFrame([{"title": "A"}, {"title": "B"}], index=[10, 11])

    assert selected_row_index(df, 11) == 11
    assert selected_row_index(df, 999) == 10
    assert selected_row_index(df, None) == 10


def test_sort_for_dashboard_orders_larger_source_index_first():
    df = pd.DataFrame(
        [
            {"title": "Oldest"},
            {"title": "Middle"},
            {"title": "Newest"},
        ],
        index=[0, 5, 9],
    )

    sorted_df = sort_for_dashboard(df)

    assert list(sorted_df.index) == [9, 5, 0]
    assert list(sorted_df["title"]) == ["Newest", "Middle", "Oldest"]


def test_selected_row_index_returns_none_for_empty_frame():
    df = pd.DataFrame(columns=["title"])

    assert selected_row_index(df, None) is None


def test_update_selected_row_updates_only_target_row_and_allowed_fields():
    original = pd.DataFrame(
        [
            {
                "title": "Role A",
                "application_status": "Not Applied",
                "applied_date": "",
                "notes": "",
            },
            {
                "title": "Role B",
                "application_status": "Saved",
                "applied_date": "",
                "notes": "",
            },
        ],
        index=[10, 11],
    )

    updated = update_selected_row(
        original_df=original,
        column_map=resolve_columns(original),
        row_index=11,
        application_status="Applied",
        applied_date="2026-05-20",
        notes="submitted",
    )

    assert updated.loc[11, "application_status"] == "Applied"
    assert updated.loc[11, "applied_date"] == "2026-05-20"
    assert updated.loc[11, "notes"] == "submitted"
    assert updated.loc[10, "application_status"] == "Not Applied"
    assert updated.loc[10, "applied_date"] == ""
    assert updated.loc[10, "notes"] == ""


def test_resolve_columns_supports_chinese_and_english_aliases():
    df = pd.DataFrame(
        [
            {
                "Company": "Example AG",
                "Title": "Data Scientist",
                "Location": "Berlin",
                "Fit Score": 88,
                "Priority": "High",
                "German Required?": "No",
                "公司重點介紹": "公司介紹",
                "JD 重點說明（需要哪些技能）": "技能需求",
                "Why it fits your CV": "很適合",
                "Main risks / gaps": "風險",
                "URL": "https://example.com/job",
                "application_status": "Not Applied",
                "applied_date": "",
                "notes": "",
            }
        ]
    )

    mapping = resolve_columns(df)

    assert mapping["company"] == "Company"
    assert mapping["title"] == "Title"
    assert mapping["location"] == "Location"
    assert mapping["match_score"] == "Fit Score"
    assert mapping["priority"] == "Priority"
    assert mapping["german_required"] == "German Required?"
    assert mapping["company_summary"] == "公司重點介紹"
    assert mapping["jd_summary"] == "JD 重點說明（需要哪些技能）"
    assert mapping["fit_reason"] == "Why it fits your CV"
    assert mapping["risk_note"] == "Main risks / gaps"
    assert mapping["url"] == "URL"


def test_selector_label_is_meaningful_and_not_row_based():
    row = pd.Series(
        {
            "Company": "Example AG",
            "Title": "Data Scientist",
            "Fit Score": 91,
            "application_status": "Applied",
        }
    )
    mapping = {
        "company": "Company",
        "title": "Title",
        "match_score": "Fit Score",
        "application_status": "application_status",
    }

    label = selector_label(row, mapping)

    assert "Example AG" in label
    assert "Data Scientist" in label
    assert "Score: 91" in label
    assert "Status: Applied" in label
    assert "Row" not in label


def test_value_for_field_returns_empty_for_missing_or_nan():
    row = pd.Series({"Company": None})
    mapping = {"company": "Company"}

    assert value_for_field(row, mapping, "company") == ""
    assert value_for_field(row, mapping, "title") == ""
