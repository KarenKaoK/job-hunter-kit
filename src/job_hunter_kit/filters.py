from __future__ import annotations

from job_hunter_kit.models import FilterResult, JobPosting, SearchConfig


def filter_jobs(jobs: list[JobPosting], config: SearchConfig) -> list[FilterResult]:
    return [filter_job(job, config) for job in jobs]


def included_jobs(jobs: list[JobPosting], config: SearchConfig) -> list[JobPosting]:
    return [
        result.job
        for result in filter_jobs(jobs, config)
        if result.decision == "include"
    ]


def filter_job(job: JobPosting, config: SearchConfig) -> FilterResult:
    include_matches = _find_include_matches(job, config)
    exclude_matches = _find_exclude_matches(job, config)

    if exclude_matches:
        return FilterResult(
            job=job,
            decision="exclude",
            matched_include_rules=include_matches,
            matched_exclude_rules=exclude_matches,
            reasons=["Matched exclude rule."],
        )

    if include_matches:
        return FilterResult(
            job=job,
            decision="include",
            matched_include_rules=include_matches,
            matched_exclude_rules=[],
            reasons=["Matched include rule and no exclude rules."],
        )

    return FilterResult(
        job=job,
        decision="exclude",
        matched_include_rules=[],
        matched_exclude_rules=[],
        reasons=["Did not match any include rule."],
    )


def _find_include_matches(job: JobPosting, config: SearchConfig) -> list[str]:
    matches: list[str] = []

    matches.extend(
        _keyword_matches(
            values=config.include.title_keywords,
            text=job.title,
            rule_name="include.title_keywords",
        )
    )
    matches.extend(
        _keyword_matches(
            values=config.include.keywords,
            text=_searchable_text(job),
            rule_name="include.keywords",
        )
    )
    matches.extend(
        _keyword_matches(
            values=config.include.locations,
            text=job.location,
            rule_name="include.locations",
        )
    )
    matches.extend(
        _keyword_matches(
            values=config.include.work_modes,
            text=job.work_mode or "",
            rule_name="include.work_modes",
        )
    )

    if config.sources:
        matches.extend(
            _keyword_matches(
                values=config.sources,
                text=job.source,
                rule_name="sources",
            )
        )

    return matches


def _find_exclude_matches(job: JobPosting, config: SearchConfig) -> list[str]:
    matches: list[str] = []

    matches.extend(
        _keyword_matches(
            values=config.exclude.title_keywords,
            text=job.title,
            rule_name="exclude.title_keywords",
        )
    )
    matches.extend(
        _keyword_matches(
            values=config.exclude.keywords,
            text=_searchable_text(job),
            rule_name="exclude.keywords",
        )
    )
    matches.extend(
        _keyword_matches(
            values=config.exclude.locations,
            text=job.location,
            rule_name="exclude.locations",
        )
    )
    matches.extend(
        _keyword_matches(
            values=config.exclude.work_modes,
            text=job.work_mode or "",
            rule_name="exclude.work_modes",
        )
    )
    matches.extend(
        _keyword_matches(
            values=config.exclude.language_requirements,
            text=" ".join([job.language or "", job.description]),
            rule_name="exclude.language_requirements",
        )
    )

    return matches


def _keyword_matches(values: list[str], text: str, rule_name: str) -> list[str]:
    normalized_text = text.casefold()
    return [
        f"{rule_name}:{value}"
        for value in values
        if value.casefold() in normalized_text
    ]


def _searchable_text(job: JobPosting) -> str:
    return " ".join(
        [
            job.title,
            job.company,
            job.location,
            job.source,
            job.description,
            job.work_mode or "",
            job.language or "",
        ]
    )
