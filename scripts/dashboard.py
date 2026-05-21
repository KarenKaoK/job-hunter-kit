from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Ensure the script loads local source code even if an older package is installed.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from job_hunter_kit.dashboard_data import (
    APPLICATION_STATUS_OPTIONS,
    COMPACT_LIST_FIELDS,
    DETAIL_READONLY_FIELDS,
    DashboardPaths,
    filter_dataframe,
    load_or_bootstrap_dataframe,
    resolve_columns,
    save_dataframe,
    selected_row_index,
    update_selected_row,
    value_for_field,
)


DEFAULT_CSV_PATH = Path("data/analyzed_jobs.csv")
DEFAULT_EXCEL_PATH = Path("output/linked_jobs_analyzed.xlsx")
DEFAULT_EXCEL_SHEET = "job_ranking"
SAVE_MESSAGE_KEY = "_save_success_message"


def main() -> None:
    st.set_page_config(page_title="job-hunter-kit dashboard", layout="wide")
    st.title("job-hunter-kit dashboard")

    paths = DashboardPaths(
        csv_path=DEFAULT_CSV_PATH,
        excel_path=DEFAULT_EXCEL_PATH,
        excel_sheet=DEFAULT_EXCEL_SHEET,
    )

    try:
        df = load_or_bootstrap_dataframe(paths)
    except Exception as error:
        st.error(str(error))
        st.stop()

    pending_message = st.session_state.pop(SAVE_MESSAGE_KEY, "")
    if pending_message:
        st.success(pending_message)

    column_map = resolve_columns(df)

    st.caption(f"Rows loaded: {len(df)}")

    keyword = st.text_input(
        "Keyword search",
        placeholder="company, title, skills_required, jd_summary",
    )

    filter_col_1, filter_col_2, filter_col_3, filter_col_4 = st.columns(4)
    priorities: list[str] = []
    german_required_values: list[str] = []
    application_status_values: list[str] = []
    min_match_score = 0.0

    priority_col = column_map.get("priority")
    if priority_col and priority_col in df.columns:
        priority_options = sorted(
            value for value in df[priority_col].dropna().astype(str).unique() if value
        )
        priorities = filter_col_1.multiselect("priority", options=priority_options)
    else:
        filter_col_1.caption("priority column not found")

    german_col = column_map.get("german_required")
    if german_col and german_col in df.columns:
        german_options = sorted(
            value for value in df[german_col].dropna().astype(str).unique() if value
        )
        german_required_values = filter_col_2.multiselect(
            "german_required",
            options=german_options,
        )
    else:
        filter_col_2.caption("german_required column not found")

    application_status_values = filter_col_3.multiselect(
        "application_status",
        options=APPLICATION_STATUS_OPTIONS,
    )

    max_match_score = 100.0
    match_score_col = column_map.get("match_score")
    if match_score_col and match_score_col in df.columns:
        match_score_numeric = pd.to_numeric(
            df[match_score_col],
            errors="coerce",
        )
        max_candidate = match_score_numeric.max()
        try:
            max_match_score = float(max_candidate)
        except Exception:
            max_match_score = 100.0
        if max_match_score < 0:
            max_match_score = 0.0
    min_match_score = float(
        filter_col_4.number_input(
            "minimum match_score",
            min_value=0.0,
            max_value=max_match_score if max_match_score > 0 else 100.0,
            value=0.0,
            step=1.0,
        )
    )

    filtered_df = filter_dataframe(
        df=df,
        column_map=column_map,
        keyword=keyword,
        priorities=priorities,
        german_required_values=german_required_values,
        application_status_values=application_status_values,
        min_match_score=min_match_score,
    )

    st.caption(f"Filtered rows: {len(filtered_df)}")

    if filtered_df.empty:
        st.info("No jobs match the current filters.")
        st.stop()

    list_columns = [
        column_map[field]
        for field in COMPACT_LIST_FIELDS
        if field in column_map and column_map[field] in filtered_df.columns
    ]
    if not list_columns:
        st.warning("None of the compact list columns are available.")
        st.stop()

    st.subheader("Jobs")
    compact_view_df = filtered_df[list_columns].reset_index().rename(
        columns={"index": "_source_index"}
    )

    selected_source_index: int | None = None
    data_event = st.dataframe(
        compact_view_df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = []
    if hasattr(data_event, "selection"):
        selected_rows = getattr(data_event.selection, "rows", []) or []

    if selected_rows:
        selected_row_position = int(selected_rows[0])
        selected_source_index = int(compact_view_df.iloc[selected_row_position]["_source_index"])
    else:
        selected_source_index = selected_row_index(filtered_df, None)

    if selected_source_index is None:
        st.info("No selectable rows.")
        st.stop()

    selected_job = filtered_df.loc[selected_source_index]
    selected_job_key = _selected_job_key(selected_job, int(selected_source_index))

    st.subheader("Selected Job Detail")
    st.markdown(f"**Company:** {value_for_field(selected_job, column_map, 'company') or 'N/A'}")
    st.markdown(f"**Title:** {value_for_field(selected_job, column_map, 'title') or 'N/A'}")
    st.markdown(f"**Location:** {value_for_field(selected_job, column_map, 'location') or 'N/A'}")

    url_value = value_for_field(selected_job, column_map, "url")
    if url_value:
        st.markdown(f"**URL:** [Open job posting]({url_value})")
    else:
        st.markdown("**URL:** N/A")

    st.markdown(
        f"**Match Score:** {value_for_field(selected_job, column_map, 'match_score') or 'N/A'}"
    )

    if "priority" in column_map:
        st.markdown(
            f"**Priority:** {value_for_field(selected_job, column_map, 'priority') or 'N/A'}"
        )
    if "german_required" in column_map:
        st.markdown(
            f"**German Required:** {value_for_field(selected_job, column_map, 'german_required') or 'N/A'}"
        )

    long_sections = [
        ("Company Summary", "company_summary"),
        ("JD Summary", "jd_summary"),
        ("Skills Required", "skills_required"),
        ("Fit Reason", "fit_reason"),
        ("Risk Note", "risk_note"),
    ]
    for title, field in long_sections:
        value = value_for_field(selected_job, column_map, field)
        st.markdown(f"### {title}")
        st.markdown(value if value else "_N/A_")

    st.subheader("Application Edit")
    status_widget_key = f"application_status_{selected_job_key}"
    applied_date_widget_key = f"applied_date_{selected_job_key}"
    notes_widget_key = f"notes_{selected_job_key}"

    current_status = value_for_field(selected_job, column_map, "application_status")
    current_status = (
        current_status if current_status in APPLICATION_STATUS_OPTIONS else "Not Applied"
    )
    current_applied_date = value_for_field(selected_job, column_map, "applied_date")
    current_notes = value_for_field(selected_job, column_map, "notes")

    edited_status = st.selectbox(
        "application_status",
        options=APPLICATION_STATUS_OPTIONS,
        index=APPLICATION_STATUS_OPTIONS.index(current_status),
        key=status_widget_key,
    )
    edited_applied_date = st.text_input(
        "applied_date",
        value=current_applied_date,
        key=applied_date_widget_key,
    )
    edited_notes = st.text_area(
        "notes",
        value=current_notes,
        height=140,
        key=notes_widget_key,
    )

    if st.button("Save", type="primary"):
        updated = update_selected_row(
            original_df=df,
            column_map=column_map,
            row_index=int(selected_source_index),
            application_status=st.session_state[status_widget_key],
            applied_date=st.session_state[applied_date_widget_key],
            notes=st.session_state[notes_widget_key],
        )
        save_dataframe(paths.csv_path, updated)
        st.session_state[SAVE_MESSAGE_KEY] = f"Saved selected row to {paths.csv_path}"
        st.rerun()


def _selected_job_key(selected_job: pd.Series, row_index: int) -> str:
    for key in ("job_id", "Job ID"):
        value = str(selected_job.get(key, "")).strip()
        if value:
            return _safe_widget_key(value)
    for key in ("url", "URL", "Job Link"):
        value = str(selected_job.get(key, "")).strip()
        if value:
            return _safe_widget_key(value)
    return f"row_{row_index}"


def _safe_widget_key(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value)


if __name__ == "__main__":
    main()
