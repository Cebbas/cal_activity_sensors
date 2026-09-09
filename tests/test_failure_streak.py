"""Tests for FailureStreakTracker's retry/backoff and repair issue,
exercised through both coordinators that share it.

A source shouldn't get escalated to a user-visible repair issue on the first
failed poll (a momentary blip) - only after FAILURE_THRESHOLD consecutive
failures. Recovery clears the issue immediately.
"""
from unittest.mock import patch

from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cal_activity.activity import ActivitySensorCoordinator
from custom_components.cal_activity.const import CONF_NAME, CONF_SOURCES, DOMAIN


def _issue(hass, entry_id):
    return ir.async_get(hass).async_get_issue(DOMAIN, f"failed_sources_{entry_id}")


async def _make_coordinator(hass) -> tuple[ActivitySensorCoordinator, str]:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_NAME: "Fotboll", CONF_SOURCES: ["calendar.flaky"]}
    )
    entry.add_to_hass(hass)
    return ActivitySensorCoordinator(hass, entry), entry.entry_id


async def _poll(coordinator, failed: list[str]):
    async def _fake(*_args, **_kwargs):
        return [], failed

    with patch("custom_components.cal_activity.activity.fetch_matching_events", side_effect=_fake):
        await coordinator._async_update_data()


async def test_single_blip_does_not_raise_an_issue(hass):
    coordinator, entry_id = await _make_coordinator(hass)

    await _poll(coordinator, ["calendar.flaky"])

    assert _issue(hass, entry_id) is None


async def test_two_consecutive_failures_raise_an_issue(hass):
    coordinator, entry_id = await _make_coordinator(hass)

    await _poll(coordinator, ["calendar.flaky"])
    await _poll(coordinator, ["calendar.flaky"])

    assert _issue(hass, entry_id) is not None


async def test_a_successful_poll_in_between_resets_the_streak(hass):
    coordinator, entry_id = await _make_coordinator(hass)

    await _poll(coordinator, ["calendar.flaky"])
    await _poll(coordinator, [])
    await _poll(coordinator, ["calendar.flaky"])

    assert _issue(hass, entry_id) is None


async def test_recovery_clears_the_issue(hass):
    coordinator, entry_id = await _make_coordinator(hass)

    await _poll(coordinator, ["calendar.flaky"])
    await _poll(coordinator, ["calendar.flaky"])
    assert _issue(hass, entry_id) is not None

    await _poll(coordinator, [])

    assert _issue(hass, entry_id) is None
