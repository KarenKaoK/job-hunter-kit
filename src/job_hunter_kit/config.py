from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from job_hunter_kit.models import CollectionConfig, FilterRuleConfig, SearchConfig


class ConfigError(ValueError):
    """Raised when a search config file is missing or malformed."""


def load_search_config(path: str | Path) -> SearchConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file)

    return parse_search_config(raw_config)


def parse_search_config(raw_config: Any) -> SearchConfig:
    if not isinstance(raw_config, dict):
        raise ConfigError("Config must be a YAML mapping.")

    return SearchConfig(
        collection=_parse_collection_config(raw_config.get("collection", {})),
        include=_parse_rule_config(raw_config.get("include", {}), "include"),
        exclude=_parse_rule_config(raw_config.get("exclude", {}), "exclude"),
        sources=_parse_string_list(raw_config.get("sources", []), "sources"),
    )


def _parse_collection_config(raw_collection: Any) -> CollectionConfig:
    if raw_collection is None:
        raw_collection = {}
    if not isinstance(raw_collection, dict):
        raise ConfigError("collection must be a mapping.")

    provider = _parse_string(
        raw_collection.get("provider", "jobspy"),
        "collection.provider",
    )
    if provider != "jobspy":
        raise ConfigError("collection.provider must be 'jobspy'.")

    platforms = _parse_string_list(
        raw_collection.get("platforms", ["linkedin"]),
        "collection.platforms",
    )
    unsupported_platforms = [
        platform for platform in platforms if platform != "linkedin"
    ]
    if unsupported_platforms:
        raise ConfigError("collection.platforms only supports 'linkedin' for now.")

    translation = raw_collection.get("translation", {})
    if translation is None:
        translation = {}
    if not isinstance(translation, dict):
        raise ConfigError("collection.translation must be a mapping.")

    return CollectionConfig(
        provider=provider,
        platforms=platforms or ["linkedin"],
        location=_parse_string(
            raw_collection.get("location", "Germany"),
            "collection.location",
        ),
        search_terms=_parse_string_list(
            raw_collection.get("search_terms", []),
            "collection.search_terms",
        ),
        results_per_term=_parse_positive_int(
            raw_collection.get("results_per_term", 25),
            "collection.results_per_term",
        ),
        hours_old=_parse_positive_int(
            raw_collection.get("hours_old", 72),
            "collection.hours_old",
        ),
        linkedin_fetch_description=_parse_bool(
            raw_collection.get("linkedin_fetch_description", False),
            "collection.linkedin_fetch_description",
        ),
        translation_enabled=_parse_bool(
            translation.get("enabled", False),
            "collection.translation.enabled",
        ),
        translation_provider=_parse_string(
            translation.get("provider", "google"),
            "collection.translation.provider",
        ),
        translation_target_language=_parse_string(
            translation.get("target_language", "zh-CN"),
            "collection.translation.target_language",
        ),
        translation_timeout_seconds=_parse_positive_int(
            translation.get("timeout_seconds", 15),
            "collection.translation.timeout_seconds",
        ),
    )


def _parse_rule_config(raw_rules: Any, section_name: str) -> FilterRuleConfig:
    if raw_rules is None:
        raw_rules = {}
    if not isinstance(raw_rules, dict):
        raise ConfigError(f"{section_name} must be a mapping.")

    return FilterRuleConfig(
        title_keywords=_parse_string_list(
            raw_rules.get("title_keywords", []),
            f"{section_name}.title_keywords",
        ),
        keywords=_parse_string_list(
            raw_rules.get("keywords", []),
            f"{section_name}.keywords",
        ),
        locations=_parse_string_list(
            raw_rules.get("locations", []),
            f"{section_name}.locations",
        ),
        work_modes=_parse_string_list(
            raw_rules.get("work_modes", []),
            f"{section_name}.work_modes",
        ),
        language_requirements=_parse_string_list(
            raw_rules.get("language_requirements", []),
            f"{section_name}.language_requirements",
        ),
    )


def _parse_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"{field_name} must be a list of strings.")
    if not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{field_name} must be a list of strings.")

    return [item.strip() for item in value if item.strip()]


def _parse_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be a string.")

    stripped_value = value.strip()
    if not stripped_value:
        raise ConfigError(f"{field_name} must not be empty.")

    return stripped_value


def _parse_positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{field_name} must be a positive integer.")

    return value


def _parse_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a boolean.")

    return value
