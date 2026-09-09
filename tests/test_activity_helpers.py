"""Tests for event_is_active / event_is_upcoming / event_is_today."""
from homeassistant.components.calendar import CalendarEvent
from homeassistant.util import dt as dt_util

from custom_components.cal_activity.activity import event_is_active, event_is_today, event_is_upcoming

NOW = dt_util.parse_datetime("2026-03-10T12:00:00+00:00")


def _event(start: str, end: str) -> CalendarEvent:
    return CalendarEvent(
        start=dt_util.parse_datetime(start),
        end=dt_util.parse_datetime(end),
        summary="X",
        uid="1",
    )


def test_event_is_active_when_now_is_within_range():
    ev = _event("2026-03-10T11:00:00+00:00", "2026-03-10T13:00:00+00:00")
    assert event_is_active(ev, NOW) is True


def test_event_is_active_false_before_start():
    ev = _event("2026-03-10T13:00:00+00:00", "2026-03-10T14:00:00+00:00")
    assert event_is_active(ev, NOW) is False


def test_event_is_active_false_after_end():
    ev = _event("2026-03-10T09:00:00+00:00", "2026-03-10T10:00:00+00:00")
    assert event_is_active(ev, NOW) is False


def test_event_is_active_boundary_inclusive():
    ev = _event("2026-03-10T12:00:00+00:00", "2026-03-10T12:00:00+00:00")
    assert event_is_active(ev, NOW) is True


def test_event_is_upcoming_true_when_start_is_after_now():
    ev = _event("2026-03-10T13:00:00+00:00", "2026-03-10T14:00:00+00:00")
    assert event_is_upcoming(ev, NOW) is True


def test_event_is_upcoming_false_when_already_started():
    ev = _event("2026-03-10T11:00:00+00:00", "2026-03-10T14:00:00+00:00")
    assert event_is_upcoming(ev, NOW) is False


def test_event_is_today_true_for_same_date():
    ev = _event("2026-03-10T01:00:00+00:00", "2026-03-10T02:00:00+00:00")
    assert event_is_today(ev, NOW) is True


def test_event_is_today_false_for_other_date():
    ev = _event("2026-03-11T01:00:00+00:00", "2026-03-11T02:00:00+00:00")
    assert event_is_today(ev, NOW) is False
