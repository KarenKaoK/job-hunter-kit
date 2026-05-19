from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Decision = Literal["include", "exclude"]
JobPlatform = Literal["linkedin"]


@dataclass(frozen=True)
class JobPosting:
    id: str
    title: str
    company: str
    location: str
    source: str
    description: str
    work_mode: str | None = None
    language: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class FilterRuleConfig:
    title_keywords: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    work_modes: list[str] = field(default_factory=list)
    language_requirements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CollectionConfig:
    provider: str = "jobspy"
    platforms: list[JobPlatform] = field(default_factory=lambda: ["linkedin"])
    location: str = "Germany"
    search_terms: list[str] = field(default_factory=list)
    results_per_term: int = 25
    hours_old: int = 72
    linkedin_fetch_description: bool = False
    translation_enabled: bool = False


@dataclass(frozen=True)
class SearchConfig:
    collection: CollectionConfig = field(default_factory=CollectionConfig)
    include: FilterRuleConfig = field(default_factory=FilterRuleConfig)
    exclude: FilterRuleConfig = field(default_factory=FilterRuleConfig)
    sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FilterResult:
    job: JobPosting
    decision: Decision
    matched_include_rules: list[str]
    matched_exclude_rules: list[str]
    reasons: list[str]
