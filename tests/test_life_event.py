"""Tests for life_event.py's date math (_safe_date, next_span, _end_inclusive)
and LifeEventCoordinator's manual/calendar date sourcing.

Dates are computed relative to the real "today" (dt_util.now().date()) rather
than hardcoded, so these stay correct regardless of when the suite runs -
there's no time-freezing dependency in this project.
"""
from datetime import date, datetime, timedelta
from unittest.mock import patch

from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cal_activity.const import (
    CONF_DATE,
    CONF_DATE_END,
    CONF_DATE_SOURCE,
    CONF_FILTER,
    CONF_NAME,
    CONF_RECURRING,
    CONF_SOURCES,
    DATE_SOURCE_CALENDAR,
    DATE_SOURCE_MANUAL,
    DOMAIN,
)
from custom_components.cal_activity.life_event import (
    LifeEventCoordinator,
    _end_inclusive,
    _safe_date,
    next_span,
)

TODAY = dt_util.now().date()


# ---- _safe_date ----


def test_safe_date_normal_date():
    assert _safe_date(2026, 6, 15) == date(2026, 6, 15)


def test_safe_date_feb29_on_non_leap_year_falls_back_to_feb28():
    assert _safe_date(2026, 2, 29) == date(2026, 2, 28)


def test_safe_date_feb29_on_leap_year_is_kept():
    assert _safe_date(2028, 2, 29) == date(2028, 2, 29)


def test_safe_date_other_invalid_date_still_raises():
    with pytest.raises(ValueError):
        _safe_date(2026, 4, 31)


# ---- next_span ----


def test_next_span_single_day_still_upcoming_this_year():
    start_base = TODAY + timedelta(days=5)
    start, end = next_span(start_base, 1, TODAY)
    assert start == end == date(TODAY.year, start_base.month, start_base.day)


def test_next_span_single_day_already_passed_rolls_to_next_year():
    start_base = TODAY - timedelta(days=5)
    if start_base.year != TODAY.year:
        pytest.skip("edge case only near year boundary - covered by the New Year test below")
    start, end = next_span(start_base, 1, TODAY)
    assert start == end == date(TODAY.year + 1, start_base.month, start_base.day)


def test_next_span_multiday_currently_in_progress():
    start_base = TODAY - timedelta(days=2)
    start, end = next_span(start_base, 5, TODAY)
    assert start == date(TODAY.year, start_base.month, start_base.day)
    assert end == start + timedelta(days=4)
    assert start <= TODAY <= end


def test_next_span_crossing_new_year_recognized_from_january():
    # A trip anchored Dec 30 (5 days -> Jan 3). Viewed from "today", if today
    # is itself early enough in the year that Dec 30 last year could still be
    # in progress, that in-progress span must win over the not-yet-arrived
    # "this year" Dec 30 occurrence.
    result = next_span(date(2020, 12, 30), 5, date(2026, 1, 2))
    assert result == (date(2025, 12, 30), date(2026, 1, 3))


def test_next_span_leap_day_anchor_on_non_leap_today():
    # Anchored on Feb 29 (leap day), evaluated on a non-leap year -> falls
    # back to Feb 28 without raising.
    start, end = next_span(date(2020, 2, 29), 1, date(2026, 3, 1))
    assert start == end == date(2027, 2, 28)


# ---- _end_inclusive ----


def test_end_inclusive_timed_event_end_unchanged():
    start = datetime(2026, 3, 10, 9, 0, tzinfo=dt_util.UTC)
    end = datetime(2026, 3, 10, 10, 0, tzinfo=dt_util.UTC)
    assert _end_inclusive(start, end) == date(2026, 3, 10)


def test_end_inclusive_single_all_day_event():
    # Calendar gives end == start for a genuinely single-day all-day event
    # (not advanced past it) - must not go negative.
    assert _end_inclusive(date(2026, 3, 10), date(2026, 3, 10)) == date(2026, 3, 10)


def test_end_inclusive_multiday_all_day_event_exclusive_end():
    # Calendar's all-day end is exclusive: a 3-day trip Mar 10-12 is reported
    # as start=Mar 10, end=Mar 13.
    assert _end_inclusive(date(2026, 3, 10), date(2026, 3, 13)) == date(2026, 3, 12)


# ---- LifeEventCoordinator: manual date source ----


def _manual_entry(**data) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DATE_SOURCE: DATE_SOURCE_MANUAL,
            CONF_NAME: "Farmors födelsedag",
            **data,
        },
    )


async def test_manual_upcoming_non_recurring_date(hass):
    target = TODAY + timedelta(days=10)
    entry = _manual_entry(**{CONF_DATE: target.isoformat(), CONF_RECURRING: False})
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["next_date"] == target
    assert data["is_current"] is False
    assert data["passed"] is False
    assert data["days_remaining"] == 10


async def test_manual_date_today_is_current(hass):
    entry = _manual_entry(**{CONF_DATE: TODAY.isoformat(), CONF_RECURRING: False})
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["is_current"] is True
    assert data["day_of_span"] == 1
    assert data["span_length"] == 1


async def test_manual_non_recurring_past_date_is_passed(hass):
    target = TODAY - timedelta(days=5)
    entry = _manual_entry(**{CONF_DATE: target.isoformat(), CONF_RECURRING: False})
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["passed"] is True
    assert data["is_current"] is False


async def test_manual_recurring_birthday_computes_years(hass):
    original = date(TODAY.year - 30, 6, 15)
    entry = _manual_entry(**{CONF_DATE: original.isoformat(), CONF_RECURRING: True})
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    start, _end = next_span(original, 1, TODAY)
    assert data["years"] == start.year - original.year
    assert data["passed"] is False  # recurring events are never "passed"


async def test_manual_recurring_multiday_span_in_progress_has_day_of_span(hass):
    start_base = TODAY - timedelta(days=2)
    end_base = start_base + timedelta(days=6)  # 7-day span, today is day 3
    entry = _manual_entry(
        **{CONF_DATE: start_base.isoformat(), CONF_DATE_END: end_base.isoformat(), CONF_RECURRING: True}
    )
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["is_current"] is True
    assert data["span_length"] == 7
    assert data["day_of_span"] == 3


async def test_manual_missing_date_yields_no_target(hass):
    entry = _manual_entry()
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["next_date"] is None
    assert data["days_remaining"] is None
    assert data["is_current"] is False


# ---- LifeEventCoordinator: calendar date source ----


async def test_calendar_source_picks_nearest_active_or_upcoming_event(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DATE_SOURCE: DATE_SOURCE_CALENDAR,
            CONF_SOURCES: ["calendar.trips"],
            CONF_FILTER: None,
            CONF_NAME: "Nästa resa",
        },
    )
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    start = TODAY + timedelta(days=3)
    end = start + timedelta(days=2)

    from homeassistant.components.calendar import CalendarEvent

    fake_event = CalendarEvent(
        start=datetime.combine(start, datetime.min.time(), tzinfo=dt_util.UTC),
        end=datetime.combine(end, datetime.min.time(), tzinfo=dt_util.UTC),
        summary="Resa till farmor",
        uid="1",
    )

    with patch(
        "custom_components.cal_activity.life_event.fetch_matching_events",
        return_value=([fake_event], []),
    ):
        data = await coordinator._async_update_data()

    assert data["label"] == "Resa till farmor"
    assert data["next_date"] == start


async def test_calendar_source_with_no_candidates_yields_no_target(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DATE_SOURCE: DATE_SOURCE_CALENDAR,
            CONF_SOURCES: ["calendar.trips"],
            CONF_FILTER: None,
            CONF_NAME: "Nästa resa",
        },
    )
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    with patch(
        "custom_components.cal_activity.life_event.fetch_matching_events",
        return_value=([], []),
    ):
        data = await coordinator._async_update_data()

    assert data["next_date"] is None
    assert data["label"] is None


async def test_calendar_source_passes_through_failed_sources(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DATE_SOURCE: DATE_SOURCE_CALENDAR,
            CONF_SOURCES: ["calendar.trips"],
            CONF_FILTER: None,
            CONF_NAME: "Nästa resa",
        },
    )
    entry.add_to_hass(hass)
    coordinator = LifeEventCoordinator(hass, entry)

    with patch(
        "custom_components.cal_activity.life_event.fetch_matching_events",
        return_value=([], ["calendar.trips"]),
    ):
        data = await coordinator._async_update_data()

    assert data["failed"] == ["calendar.trips"]
