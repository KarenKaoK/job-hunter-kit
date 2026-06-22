from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


EDITABLE_COLUMNS = ["application_status", "applied_date", "notes"]
COMPACT_LIST_FIELDS = [
    "company",
    "title",
    "location",
    "match_score",
    "priority",
    "german_required",
    "application_status",
]
DETAIL_READONLY_FIELDS = [
    "company",
    "title",
    "location",
    "url",
    "match_score",
    "priority",
    "german_required",
    "company_summary",
    "jd_summary",
    "skills_required",
    "fit_reason",
    "risk_note",
]
APPLICATION_STATUS_OPTIONS = [
    "Not Applied",
    "Applied",
    "Rejected",
    "Interview",
    "Saved",
    "Skipped",
    "Deleted",
]
FIELD_ALIASES = {
    "company": ["company", "Company", "公司"],
    "title": ["title", "Title", "職稱"],
    "location": ["location", "Location", "地點"],
    "url": ["url", "URL"],
    "match_score": ["match_score", "Fit Score", "fit_score"],
    "priority": ["priority", "Priority"],
    "german_required": ["german_required", "German Required?"],
    "company_summary": ["company_summary", "公司重點介紹"],
    "jd_summary": ["jd_summary", "JD 重點說明（需要哪些技能）"],
    "skills_required": ["skills_required"],
    "fit_reason": ["fit_reason", "Why it fits your CV"],
    "risk_note": ["risk_note", "Main risks / gaps", "German Risk"],
    "application_status": ["application_status"],
    "applied_date": ["applied_date"],
    "notes": ["notes"],
}


@dataclass(frozen=True)
class DashboardPaths:
    csv_path: Path
    excel_path: Path
    excel_sheet: str


def load_or_bootstrap_dataframe(paths: DashboardPaths) -> pd.DataFrame:
    if paths.csv_path.exists():
        df = pd.read_csv(paths.csv_path)
        return _normalize_dashboard_columns(df)

    if not paths.excel_path.exists():
        raise FileNotFoundError(
            f"Missing input files: {paths.csv_path} and {paths.excel_path}"
        )

    df = pd.read_excel(paths.excel_path, sheet_name=paths.excel_sheet)
    df = _normalize_dashboard_columns(df)
    save_dataframe(paths.csv_path, df)
    return df


def save_dataframe(csv_path: Path, df: pd.DataFrame) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)


def resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                mapping[field] = alias
                break
    return mapping


def filter_dataframe(
    df: pd.DataFrame,
    column_map: dict[str, str],
    keyword: str,
    priorities: list[str],
    german_required_values: list[str],
    application_status_values: list[str],
    min_match_score: float,
) -> pd.DataFrame:
    filtered = df.copy()

    if keyword.strip():
        keyword_value = keyword.strip().casefold()
        searchable_fields = ["company", "title", "skills_required", "jd_summary"]
        text_mask = pd.Series(False, index=filtered.index)
        for field in searchable_fields:
            column = column_map.get(field)
            if column in filtered.columns:
                text_mask = text_mask | filtered[column].fillna("").astype(str).str.casefold().str.contains(keyword_value)
        filtered = filtered[text_mask]

    priority_col = column_map.get("priority")
    if priorities and priority_col in filtered.columns:
        filtered = filtered[
            filtered[priority_col].fillna("").astype(str).isin(priorities)
        ]

    german_col = column_map.get("german_required")
    if german_required_values and german_col in filtered.columns:
        filtered = filtered[
            filtered[german_col].fillna("").astype(str).isin(german_required_values)
        ]

    status_col = column_map.get("application_status", "application_status")
    if application_status_values:
        filtered = filtered[
            filtered[status_col]
            .fillna("")
            .astype(str)
            .isin(application_status_values)
        ]

    match_col = column_map.get("match_score")
    if match_col in filtered.columns:
        match_scores = pd.to_numeric(filtered[match_col], errors="coerce")
        filtered = filtered[match_scores >= min_match_score]

    return filtered


def apply_edits(original_df: pd.DataFrame, edited_view_df: pd.DataFrame) -> pd.DataFrame:
    updated = original_df.copy()
    for idx in edited_view_df.index:
        if idx not in updated.index:
            continue
        for column in EDITABLE_COLUMNS:
            if column in edited_view_df.columns and column in updated.columns:
                updated.at[idx, column] = edited_view_df.at[idx, column]
    return updated


def compact_list_columns(df: pd.DataFrame) -> list[str]:
    column_map = resolve_columns(df)
    columns: list[str] = []
    for field in COMPACT_LIST_FIELDS:
        col = column_map.get(field)
        if col and col in df.columns:
            columns.append(col)
    return columns


def sort_for_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_index(ascending=False)


def selected_row_index(filtered_df: pd.DataFrame, selected_index: int | None) -> int | None:
    if filtered_df.empty:
        return None

    if selected_index is not None and selected_index in filtered_df.index:
        return selected_index

    return int(filtered_df.index[0])


def update_selected_row(
    original_df: pd.DataFrame,
    column_map: dict[str, str],
    row_index: int,
    application_status: str,
    applied_date: str,
    notes: str,
) -> pd.DataFrame:
    updated = original_df.copy()
    if row_index not in updated.index:
        return updated

    updated.at[row_index, column_map["application_status"]] = application_status
    updated.at[row_index, column_map["applied_date"]] = applied_date
    updated.at[row_index, column_map["notes"]] = notes
    return updated


def value_for_field(row: pd.Series, column_map: dict[str, str], field: str) -> str:
    column = column_map.get(field)
    if not column:
        return ""
    value = row.get(column, "")
    if pd.isna(value):
        return ""
    return str(value).strip()


def selector_label(row: pd.Series, column_map: dict[str, str]) -> str:
    company = value_for_field(row, column_map, "company") or "Unknown Company"
    title = value_for_field(row, column_map, "title") or "Unknown Title"
    score = value_for_field(row, column_map, "match_score") or "N/A"
    status = value_for_field(row, column_map, "application_status") or "Not Applied"
    return f"{company} | {title} | Score: {score} | Status: {status}"


def _normalize_dashboard_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    column_map = resolve_columns(normalized)

    if "application_status" not in column_map:
        normalized["application_status"] = ""
        column_map["application_status"] = "application_status"
    if "applied_date" not in column_map:
        normalized["applied_date"] = ""
        column_map["applied_date"] = "applied_date"
    if "notes" not in column_map:
        normalized["notes"] = ""
        column_map["notes"] = "notes"

    status_col = column_map["application_status"]
    normalized[status_col] = normalized[status_col].replace("", "Not Applied")
    normalized[status_col] = normalized[status_col].fillna("Not Applied")
    normalized[status_col] = normalized[status_col].astype(str)
    normalized[status_col] = normalized[status_col].apply(_normalize_status)

    normalized[column_map["applied_date"]] = (
        normalized[column_map["applied_date"]].fillna("").astype(str)
    )
    normalized[column_map["notes"]] = (
        normalized[column_map["notes"]].fillna("").astype(str)
    )

    # Optional fallback so keyword search still covers required field.
    if "skills_required" not in resolve_columns(normalized) and "JD 重點說明（需要哪些技能）" in normalized.columns:
        normalized["skills_required"] = normalized["JD 重點說明（需要哪些技能）"]
    return normalized


def _normalize_status(value: str) -> str:
    if value in APPLICATION_STATUS_OPTIONS:
        return value
    return "Not Applied"
