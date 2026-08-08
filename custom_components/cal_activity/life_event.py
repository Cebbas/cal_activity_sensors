"""Coordinator + date logic for countdown / life-event sensors.

Shares the calendar fetch/filter plumbing with `activity.py` (same
`fetch_matching_events`, `event_is_active`, `event_is_upcoming`) instead of
duplicating it - the only new logic here is turning either a manual date or a
matched calendar event into "how many days until/since" plus, for recurring
manual dates, an age/anniversary count.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .activity import event_is_active, event_is_upcoming, fetch_matching_events
from .activity_log import async_log
from .const import (
    CONF_DATE,
    CONF_DATE_SOURCE,
    CONF_FILTER,
    CONF_NAME,
    CONF_RECURRING,
    CONF_SOURCES,
    DATE_SOURCE_CALENDAR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)
CALENDAR_LOOKAHEAD = timedelta(days=400)


def _safe_date(year: int, month: int, day: int) -> date:
    """Build a date, falling back Feb 29 -> Feb 28 on non-leap years."""
    try:
        return date(year, month, day)
    except ValueError:
        if (month, day) == (2, 29):
            return date(year, 2, 28)
        raise


def next_occurrence(base: date, today: date) -> date:
    """Next date sharing `base`'s month/day, this year or next."""
    candidate = _safe_date(today.year, base.month, base.day)
    if candidate < today:
        candidate = _safe_date(today.year + 1, base.month, base.day)
    return candidate


def _as_date(value) -> date:
    return value.date() if isinstance(value, datetime) else value


class LifeEventCoordinator(DataUpdateCoordinator):
    """Computes days-remaining for a countdown/life-event sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=f"cal_activity_life_{entry.entry_id}", update_interval=SCAN_INTERVAL
        )
        self.entry = entry
        self._last_failed: set[str] = set()

    async def _async_update_data(self):
        entry = self.entry
        date_source = entry.data.get(CONF_DATE_SOURCE)
        now = dt_util.now()
        today = now.date()

        if date_source == DATE_SOURCE_CALENDAR:
            sources: list[str] = entry.data.get(CONF_SOURCES, [])
            rule = entry.data.get(CONF_FILTER)
            events, failed = await fetch_matching_events(
                self.hass, sources, rule, now - timedelta(hours=1), now + CALENDAR_LOOKAHEAD
            )
            candidates = [e for e in events if event_is_active(e, now) or event_is_upcoming(e, now)]
            target = candidates[0] if candidates else None
            next_date = _as_date(target.start) if target else None
            label = target.summary if target else None
            years = None
            passed = False

            failed_set = set(failed)
            if failed_set and failed_set != self._last_failed:
                await async_log(self.hass, entry.entry_id, "Källa svarar inte: " + ", ".join(failed))
            elif not failed_set and self._last_failed:
                await async_log(self.hass, entry.entry_id, "Alla källor svarar igen")
            self._last_failed = failed_set
        else:
            failed = []
            label = entry.data.get(CONF_NAME)
            date_str = entry.data.get(CONF_DATE)
            if not date_str:
                next_date = None
                years = None
                passed = False
            else:
                original = date.fromisoformat(date_str)
                if entry.data.get(CONF_RECURRING, True):
                    next_date = next_occurrence(original, today)
                    years = next_date.year - original.year
                    passed = False
                else:
                    next_date = original
                    years = None
                    passed = original < today

        days_remaining = (next_date - today).days if next_date else None
        return {
            "next_date": next_date,
            "days_remaining": days_remaining,
            "label": label,
            "years": years,
            "passed": passed,
            "failed": failed,
        }


async def async_get_or_create_life_event_coordinator(
    hass: HomeAssistant, entry: ConfigEntry
) -> LifeEventCoordinator:
    """One coordinator per entry, shared between the binary_sensor and sensor platforms."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    key = f"{entry.entry_id}_life_coordinator"
    coordinator = domain_data.get(key)
    if coordinator is None:
        coordinator = LifeEventCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        domain_data[key] = coordinator
    return coordinator
