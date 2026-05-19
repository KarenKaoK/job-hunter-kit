import pytest

from job_hunter_kit.config import ConfigError, parse_search_config


def test_parse_search_config_with_valid_rules():
    config = parse_search_config(
        {
            "collection": {
                "search_terms": ["Data Scientist"],
                "results_per_term": 10,
                "hours_old": 24,
            },
            "include": {
                "title_keywords": ["Data Scientist"],
                "locations": ["Berlin"],
            },
            "exclude": {
                "keywords": ["unpaid"],
                "language_requirements": ["native german"],
            },
            "sources": ["sample"],
        }
    )

    assert config.collection.platforms == ["linkedin"]
    assert config.collection.location == "Germany"
    assert config.collection.search_terms == ["Data Scientist"]
    assert config.collection.results_per_term == 10
    assert config.collection.hours_old == 24
    assert config.include.title_keywords == ["Data Scientist"]
    assert config.include.locations == ["Berlin"]
    assert config.exclude.keywords == ["unpaid"]
    assert config.exclude.language_requirements == ["native german"]
    assert config.sources == ["sample"]


def test_parse_search_config_defaults_missing_sections_to_empty_rules():
    config = parse_search_config({})

    assert config.include.title_keywords == []
    assert config.include.keywords == []
    assert config.exclude.keywords == []
    assert config.sources == []
    assert config.collection.provider == "jobspy"
    assert config.collection.platforms == ["linkedin"]
    assert config.collection.location == "Germany"
    assert config.collection.search_terms == []
    assert config.collection.results_per_term == 25
    assert config.collection.hours_old == 72


def test_parse_search_config_rejects_non_mapping():
    with pytest.raises(ConfigError, match="Config must be a YAML mapping"):
        parse_search_config(["not", "a", "mapping"])


def test_parse_search_config_rejects_non_string_lists():
    with pytest.raises(ConfigError, match="include.keywords"):
        parse_search_config({"include": {"keywords": ["python", 123]}})


def test_parse_search_config_rejects_unsupported_collection_platform():
    with pytest.raises(ConfigError, match="only supports 'linkedin'"):
        parse_search_config({"collection": {"platforms": ["indeed"]}})


def test_parse_search_config_rejects_invalid_collection_values():
    with pytest.raises(ConfigError, match="collection.results_per_term"):
        parse_search_config({"collection": {"results_per_term": 0}})

    with pytest.raises(ConfigError, match="collection.translation.enabled"):
        parse_search_config({"collection": {"translation": {"enabled": "yes"}}})
