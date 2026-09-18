"""Tests for calendar_sync.async_sync_birthday_occurrence: creates one
all-day event per occurrence, idempotently, in the target calendar.
"""
from datetime import date

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.cal_activity.calendar_sync import (
    async_clear,
    async_sync_birthday_occurrence,
)
from custom_components.cal_activity.const import DOMAIN


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    return entry


async def test_creates_event_on_first_sync(hass):
    calls = async_mock_service(hass, "calendar", "create_event")
    entry = _entry(hass)

    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )

    assert len(calls) == 1
    assert calls[0].data == {
        "entity_id": "calendar.family",
        "summary": "Naomis Födelsedag",
        "start_date": "2027-04-06",
        "end_date": "2027-04-07",
    }


async def test_does_not_recreate_the_same_occurrence(hass):
    calls = async_mock_service(hass, "calendar", "create_event")
    entry = _entry(hass)

    for _ in range(3):
        await async_sync_birthday_occurrence(
            hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
        )

    assert len(calls) == 1


async def test_resyncs_when_occurrence_advances_to_next_year(hass):
    calls = async_mock_service(hass, "calendar", "create_event")
    entry = _entry(hass)

    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )
    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2028, 4, 6), date(2028, 4, 6)
    )

    assert len(calls) == 2


async def test_resyncs_when_target_calendar_changes(hass):
    calls = async_mock_service(hass, "calendar", "create_event")
    entry = _entry(hass)

    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )
    await async_sync_birthday_occurrence(
        hass, entry, "calendar.other", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )

    assert len(calls) == 2


async def test_failed_service_call_is_not_recorded_as_synced(hass):
    entry = _entry(hass)

    async def _boom(call):
        raise RuntimeError("boom")

    hass.services.async_register("calendar", "create_event", _boom)

    # Should not raise - a source failing to accept the event shouldn't take
    # the sensor's own coordinator update down with it.
    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )

    calls = async_mock_service(hass, "calendar", "create_event")
    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )
    # A retry after a failed attempt should still try to create the event -
    # the failure must not have been recorded as if it had succeeded.
    assert len(calls) == 1


async def test_clear_removes_stored_sync_state(hass):
    calls = async_mock_service(hass, "calendar", "create_event")
    entry = _entry(hass)

    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )
    await async_clear(hass, entry.entry_id)
    await async_sync_birthday_occurrence(
        hass, entry, "calendar.family", "Naomis Födelsedag", date(2027, 4, 6), date(2027, 4, 6)
    )

    assert len(calls) == 2
