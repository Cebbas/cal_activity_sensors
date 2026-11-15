"""Sensors flip exactly at an event's start/end/midnight, not at the next poll."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.components.calendar import CalendarEvent
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.cal_activity.activity import (
    ActivitySensorCoordinator,
    next_activity_transition,
    next_local_midnight,
)
from custom_components.cal_activity.const import CONF_NAME, CONF_SOURCES, DOMAIN

NOW = dt_util.parse_datetime("2026-03-10T12:00:00+00:00")


def _event(start_min: int, end_min: int) -> CalendarEvent:
    return CalendarEvent(
        start=NOW + timedelta(minutes=start_min), end=NOW + timedelta(minutes=end_min), summary="Fotboll", uid="1"
    )


def test_next_transition_is_the_next_start():
    assert next_activity_transition([_event(10, 70)], NOW) == NOW + timedelta(minutes=10)


def test_next_transition_is_just_after_the_end_while_active():
    assert next_activity_transition([_event(-10, 20)], NOW) == NOW + timedelta(minutes=20, seconds=1)


def test_next_transition_falls_back_to_midnight():
    assert next_activity_transition([], NOW) == dt_util.as_utc(next_local_midnight(NOW))


async def test_listeners_are_updated_at_event_start_without_a_new_poll(hass, freezer):
    freezer.move_to(NOW)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_NAME: "Fotboll", CONF_SOURCES: ["calendar.a"]})
    entry.add_to_hass(hass)
    fetch = AsyncMock(return_value=([_event(2, 60)], []))
    with patch("custom_components.cal_activity.activity.fetch_matching_events", fetch):
        coordinator = ActivitySensorCoordinator(hass, entry)
        await coordinator.async_refresh()

    updates = []
    unsub = coordinator.async_add_listener(lambda: updates.append(dt_util.utcnow()))
    try:
        freezer.tick(timedelta(minutes=2, seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert len(updates) == 1
        assert fetch.await_count == 1  # recomputed from cached events, no refetch
    finally:
        unsub()
        coordinator.transitions.cancel()
