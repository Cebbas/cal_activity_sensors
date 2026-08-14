"""Coordinator + date logic for countdown / life-event sensors.

Shares the calendar fetch/filter plumbing with `activity.py` (same
`fetch_matching_events`, `event_is_active`, `event_is_upcoming`) instead of
duplicating it. Handles both single-day dates (birthdays, name days) and
multi-day spans (a trip), which is really the same math with `span_days == 1`
as the single-day special case.
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
    CONF_DATE_END,
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


def next_span(start_base: date, span_days: int, today: date) -> tuple[date, date]:
    """(start, end_inclusive) of the current or next occurrence of a span.

    `start_base`'s month/day anchors the span every year. `span_days == 1`
    reduces to "next date sharing this month/day, this year or next" - the
    single-day case. If we're currently inside a span that started before
    today (e.g. day 3 of a week-long trip), this correctly keeps that span
    instead of rolling forward to next year just because the start date has
    passed - it compares `today` against the span's END, not its start.

    Also checks last year's occurrence first, so a span that crosses the
    turn of the year (e.g. a New Year's trip, Dec 30 - Jan 3) is still
    recognized as "in progress" when viewed from January - not just from
    December.
    """
    start_prev_year = _safe_date(today.year - 1, start_base.month, start_base.day)
    end_prev_year = start_prev_year + timedelta(days=span_days - 1)
    if start_prev_year <= today <= end_prev_year:
        return start_prev_year, end_prev_year

    start_this_year = _safe_date(today.year, start_base.month, start_base.day)
    end_this_year = start_this_year + timedelta(days=span_days - 1)
    if today <= end_this_year:
        return start_this_year, end_this_year
    start_next_year = _safe_date(today.year + 1, start_base.month, start_base.day)
    return start_next_year, start_next_year + timedelta(days=span_days - 1)


def _as_date(value) -> date:
    return value.date() if isinstance(value, datetime) else value


def _end_inclusive(start_raw, end_raw) -> date:
    """Calendar `end` is exclusive (day after the last day) for all-day
    events, but a literal moment for timed events - normalize both to the
    inclusive last day."""
    start_d = _as_date(start_raw)
    end_d = _as_date(end_raw)
    if isinstance(start_raw, datetime) and isinstance(end_raw, datetime):
        return end_d
    return end_d - timedelta(days=1) if end_d > start_d else start_d


class LifeEventCoordinator(DataUpdateCoordinator):
    """Computes days-remaining/in-progress state for a countdown/life-event sensor."""

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
            if target:
                start = _as_date(target.start)
                end_inclusive = _end_inclusive(target.start, target.end)
            else:
                start = end_inclusive = None
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
                start = end_inclusive = None
                years = None
                passed = False
            else:
                original_start = date.fromisoformat(date_str)
                end_str = entry.data.get(CONF_DATE_END)
                original_end = date.fromisoformat(end_str) if end_str else original_start
                span_days = max((original_end - original_start).days + 1, 1)

                if entry.data.get(CONF_RECURRING, True):
                    start, end_inclusive = next_span(original_start, span_days, today)
                    years = start.year - original_start.year
                    passed = False
                else:
                    start, end_inclusive = original_start, original_start + timedelta(days=span_days - 1)
                    years = None
                    passed = today > end_inclusive

        if start is None:
            days_remaining = None
            is_current = False
            day_of_span = None
            span_length = None
        else:
            is_current = start <= today <= end_inclusive
            span_length = (end_inclusive - start).days + 1
            day_of_span = (today - start).days + 1 if is_current else None
            if today < start:
                days_remaining = (start - today).days
            else:
                days_remaining = (end_inclusive - today).days

        return {
            "next_date": start,
            "end_date": end_inclusive,
            "days_remaining": days_remaining,
            "label": label,
            "years": years,
            "passed": passed,
            "is_current": is_current,
            "day_of_span": day_of_span,
            "span_length": span_length,
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
