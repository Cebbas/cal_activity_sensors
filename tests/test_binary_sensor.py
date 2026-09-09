"""Tests for the two binary_sensor entities' is_on/extra_state_attributes logic.

Uses a minimal fake coordinator (just exposes `.data`) rather than a real
DataUpdateCoordinator - CoordinatorEntity.__init__ only reads that attribute
for the properties under test here.
"""
from datetime import date, timedelta

from homeassistant.components.calendar import CalendarEvent
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cal_activity.binary_sensor import ActivityBinarySensor, CountdownBinarySensor
from custom_components.cal_activity.const import CONF_NAME, CONF_TRIGGER_MODE, DOMAIN, TRIGGER_MODE_TODAY

NOW = dt_util.parse_datetime("2026-03-10T12:00:00+00:00")


class _FakeCoordinator:
    def __init__(self, data):
        self.data = data


def _event(start: str, end: str, summary="X", location=None) -> CalendarEvent:
    return CalendarEvent(
        start=dt_util.parse_datetime(start),
        end=dt_util.parse_datetime(end),
        summary=summary,
        location=location,
        uid="1",
    )


def _activity_sensor(events, trigger_mode=None, failed=None) -> ActivityBinarySensor:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_NAME: "Fotboll", CONF_TRIGGER_MODE: trigger_mode})
    coordinator = _FakeCoordinator({"events": events, "failed": failed or []})
    sensor = ActivityBinarySensor(coordinator, entry)
    sensor.hass = None
    return sensor


def _patch_now(monkeypatch):
    monkeypatch.setattr(dt_util, "now", lambda: NOW)


def test_activity_is_on_true_when_event_active_now(monkeypatch):
    _patch_now(monkeypatch)
    events = [_event("2026-03-10T11:00:00+00:00", "2026-03-10T13:00:00+00:00")]
    sensor = _activity_sensor(events)
    assert sensor.is_on is True


def test_activity_is_on_false_when_no_event_active(monkeypatch):
    _patch_now(monkeypatch)
    events = [_event("2026-03-11T11:00:00+00:00", "2026-03-11T13:00:00+00:00")]
    sensor = _activity_sensor(events)
    assert sensor.is_on is False


def test_activity_today_trigger_mode_ignores_active_window(monkeypatch):
    _patch_now(monkeypatch)
    # Later today, but not active right now - today mode should still be on.
    events = [_event("2026-03-10T18:00:00+00:00", "2026-03-10T19:00:00+00:00")]
    sensor = _activity_sensor(events, trigger_mode=TRIGGER_MODE_TODAY)
    assert sensor.is_on is True


def test_activity_attributes_include_current_and_next_event(monkeypatch):
    _patch_now(monkeypatch)
    active = _event("2026-03-10T11:00:00+00:00", "2026-03-10T13:00:00+00:00", summary="Nu")
    upcoming = _event("2026-03-12T09:00:00+00:00", "2026-03-12T10:00:00+00:00", summary="Sen", location="Arenan")
    sensor = _activity_sensor([active, upcoming])

    attrs = sensor.extra_state_attributes

    assert attrs["current_event"] == "Nu"
    assert "active_until" in attrs
    assert attrs["next_event"] == "Sen"
    assert attrs["location"] == "Arenan"


def test_activity_today_mode_omits_active_until(monkeypatch):
    _patch_now(monkeypatch)
    active = _event("2026-03-10T11:00:00+00:00", "2026-03-10T13:00:00+00:00", summary="Nu")
    sensor = _activity_sensor([active], trigger_mode=TRIGGER_MODE_TODAY)

    attrs = sensor.extra_state_attributes

    assert "active_until" not in attrs


def test_activity_failed_sources_surfaced_when_present(monkeypatch):
    _patch_now(monkeypatch)
    sensor = _activity_sensor([], failed=["calendar.flaky"])
    assert sensor.extra_state_attributes["failed_sources"] == ["calendar.flaky"]


def test_activity_no_failed_key_when_all_sources_ok(monkeypatch):
    _patch_now(monkeypatch)
    sensor = _activity_sensor([])
    assert "failed_sources" not in sensor.extra_state_attributes


def _countdown_sensor(data) -> CountdownBinarySensor:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_NAME: "Farmors födelsedag"})
    coordinator = _FakeCoordinator(data)
    sensor = CountdownBinarySensor(coordinator, entry)
    sensor.hass = None
    return sensor


def test_countdown_is_on_reflects_is_current():
    assert _countdown_sensor({"is_current": True}).is_on is True
    assert _countdown_sensor({"is_current": False}).is_on is False


def test_countdown_phase_in_progress():
    sensor = _countdown_sensor({"is_current": True, "passed": False})
    assert sensor.extra_state_attributes["phase"] == "in_progress"


def test_countdown_phase_upcoming():
    sensor = _countdown_sensor({"is_current": False, "passed": False})
    assert sensor.extra_state_attributes["phase"] == "upcoming"


def test_countdown_phase_passed():
    sensor = _countdown_sensor({"is_current": False, "passed": True})
    attrs = sensor.extra_state_attributes
    assert attrs["phase"] == "passed"
    assert attrs["passed"] is True


def test_countdown_days_until_start_computed_from_next_date(monkeypatch):
    _patch_now(monkeypatch)
    next_date = NOW.date() + timedelta(days=5)
    sensor = _countdown_sensor({"is_current": False, "passed": False, "next_date": next_date})

    attrs = sensor.extra_state_attributes

    assert attrs["next_date"] == next_date.isoformat()
    assert attrs["days_until_start"] == 5


def test_countdown_multiday_span_includes_span_attributes():
    sensor = _countdown_sensor(
        {
            "is_current": True,
            "passed": False,
            "span_length": 3,
            "day_of_span": 2,
            "end_date": date(2026, 3, 12),
        }
    )

    attrs = sensor.extra_state_attributes

    assert attrs["span_length"] == 3
    assert attrs["day_of_span"] == 2
    assert attrs["end_date"] == "2026-03-12"


def test_countdown_single_day_omits_span_attributes():
    sensor = _countdown_sensor({"is_current": True, "passed": False, "span_length": 1})
    attrs = sensor.extra_state_attributes
    assert "span_length" not in attrs
    assert "end_date" not in attrs


def test_countdown_failed_sources_surfaced_when_present():
    sensor = _countdown_sensor({"is_current": False, "passed": False, "failed": ["calendar.flaky"]})
    assert sensor.extra_state_attributes["failed_sources"] == ["calendar.flaky"]
