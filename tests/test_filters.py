"""Unit tests for the shared include/exclude filter rule in activity.py.

Pure functions (plain dicts in, dict/bool out) so they're tested directly
without a running Home Assistant instance.
"""
from custom_components.cal_activity.activity import _extract_field_text, _matches_filter

EVENT = {
    "summary": "Fotboll // FC Zoo",
    "description": "Ta med vattenflaska",
    "location": "Zoo-planen",
}


def test_extract_field_any_joins_all_fields():
    text = _extract_field_text(EVENT, "any")
    assert "Fotboll" in text and "vattenflaska" in text and "Zoo-planen" in text


def test_extract_field_missing_returns_empty_string():
    assert _extract_field_text({}, "summary") == ""


def test_no_rule_always_matches():
    assert _matches_filter(EVENT, None) is True
    assert _matches_filter(EVENT, {}) is True


def test_include_keyword_match():
    assert _matches_filter(EVENT, {"include": ["zoo"]}) is True


def test_include_keyword_no_match_excludes():
    assert _matches_filter(EVENT, {"include": ["hockey"]}) is False


def test_exclude_keyword_match_excludes():
    assert _matches_filter(EVENT, {"exclude": ["zoo"]}) is False


def test_include_and_exclude_combined():
    rule = {"include": ["fotboll"], "exclude": ["zoo"]}
    assert _matches_filter(EVENT, rule) is False


def test_case_insensitive_by_default():
    assert _matches_filter(EVENT, {"include": ["FOTBOLL"]}) is True


def test_case_sensitive_mismatch_fails():
    rule = {"include": ["FOTBOLL"], "case_sensitive": True}
    assert _matches_filter(EVENT, rule) is False


def test_field_targets_only_that_field():
    rule = {"field": "location", "include": ["fotboll"]}
    assert _matches_filter(EVENT, rule) is False
    rule = {"field": "location", "include": ["zoo-planen"]}
    assert _matches_filter(EVENT, rule) is True


def test_regex_mode_matches_pattern():
    rule = {"use_regex": True, "include": [r"^Fotboll \/\/"]}
    assert _matches_filter(EVENT, rule) is True


def test_regex_invalid_pattern_treated_as_no_match():
    rule = {"use_regex": True, "include": ["("]}
    assert _matches_filter(EVENT, rule) is False
