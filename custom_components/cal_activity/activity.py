"""Shared coordinator + calendar-fetch/filter logic for activity sensors.

Standalone from any other integration: sensors here just poll whichever
`calendar.*` entities you point them at via the built-in `calendar.get_events`
service and apply one include/exclude rule, so there is nothing to import
from a calendar-merging integration even if one happens to be installed too.
"""
from __future__ import annotations

from datetime import timedelta
import logging
import re

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .activity_log import async_log
from .const import CONF_FILTER, CONF_NAME, CONF_SOURCES, DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)
# How many consecutive failed polls a source needs before it's surfaced as a
# repair issue - a single blip (a flaky proxy, a momentary timeout) shouldn't
# raise a user-visible issue on every poll; it should just quietly retry.
FAILURE_THRESHOLD = 2


def _extract_field_text(item: dict, field: str) -> str:
    if field == "any":
        return " ".join(
            [item.get("summary") or "", item.get("description") or "", item.get("location") or ""]
        )
    return item.get(field) or ""


def _matches_filter(item: dict, rule: dict | None) -> bool:
    """Apply the sensor's include/exclude rule (keyword or regex) to a raw event dict."""
    if not rule:
        return True

    case_sensitive = rule.get("case_sensitive", False)
    use_regex = rule.get("use_regex", False)
    text = _extract_field_text(item, rule.get("field", "any"))
    text_cmp = text if case_sensitive else text.lower()
    flags = 0 if case_sensitive else re.IGNORECASE

    def _one_matches(pattern_or_word: str) -> bool:
        if use_regex:
            try:
                return re.search(pattern_or_word, text, flags) is not None
            except re.error as err:
                _LOGGER.warning("Ogiltigt regex-mönster %r: %s", pattern_or_word, err)
                return False
        word_cmp = pattern_or_word if case_sensitive else pattern_or_word.lower()
        return word_cmp in text_cmp

    include = rule.get("include") or []
    if include and not any(_one_matches(w) for w in include):
        return False

    exclude = rule.get("exclude") or []
    if any(_one_matches(w) for w in exclude):
        return False

    return True


async def fetch_matching_events(
    hass: HomeAssistant, sources: list[str], rule: dict | None, start, end
) -> tuple[list[CalendarEvent], list[str]]:
    """Query every source calendar entity and apply the shared filter rule.

    Returns (events, failed_entity_ids) so callers can surface source errors.
    """
    events: list[CalendarEvent] = []
    failed: list[str] = []

    for entity_id in sources:
        try:
            response = await hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": entity_id,
                    "start_date_time": start.isoformat(),
                    "end_date_time": end.isoformat(),
                },
                blocking=True,
                return_response=True,
            )
        except Exception as err:  # noqa: BLE001 - keep the other sources working if one fails
            _LOGGER.warning("Could not fetch events from %s: %s", entity_id, err)
            failed.append(entity_id)
            continue

        for item in response.get(entity_id, {}).get("events", []):
            if not _matches_filter(item, rule):
                continue
            # parse_date first: parse_datetime "succeeds" on a pure date string too
            # (as a naive midnight datetime), which breaks all-day events.
            start_val = dt_util.parse_date(item["start"]) or dt_util.parse_datetime(item["start"])
            end_val = dt_util.parse_date(item["end"]) or dt_util.parse_datetime(item["end"])
            events.append(
                CalendarEvent(
                    start=start_val,
                    end=end_val,
                    summary=item.get("summary", ""),
                    description=item.get("description"),
                    location=item.get("location"),
                    uid=item.get("uid") or item.get("summary") or "",
                )
            )

    events.sort(key=lambda e: str(e.start))
    return events, failed


def event_is_active(event, now) -> bool:
    return str(event.start) <= str(now) <= str(event.end)


def event_is_upcoming(event, now) -> bool:
    return str(event.start) > str(now)


def event_is_today(event, now) -> bool:
    return str(event.start)[:10] == str(now.date())


def _failed_sources_issue_id(entry_id: str) -> str:
    return f"failed_sources_{entry_id}"


async def async_notify_failed_sources(hass: HomeAssistant, entry: ConfigEntry, failed: list[str]) -> None:
    ir.async_create_issue(
        hass,
        DOMAIN,
        _failed_sources_issue_id(entry.entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="failed_sources",
        translation_placeholders={
            "name": entry.data.get(CONF_NAME, "Cal Activity"),
            "sources": "\n".join(f"- {e}" for e in failed),
        },
    )
    await async_log(hass, entry.entry_id, "Källa svarar inte: " + ", ".join(failed))


async def async_dismiss_failed_sources(hass: HomeAssistant, entry: ConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, _failed_sources_issue_id(entry.entry_id))
    await async_log(hass, entry.entry_id, "Alla källor svarar igen")


class FailureStreakTracker:
    """Retry/backoff for a coordinator's failed-source repair issue.

    A source only escalates to a user-visible repair issue once it's failed
    FAILURE_THRESHOLD polls in a row, not on the first blip - shared between
    ActivitySensorCoordinator and LifeEventCoordinator (calendar date
    source), which otherwise duplicate this bookkeeping.
    """

    def __init__(self) -> None:
        self._streaks: dict[str, int] = {}
        self._last_notified: set[str] = set()

    async def async_update(self, hass: HomeAssistant, entry: ConfigEntry, failed: list[str]) -> None:
        failed_set = set(failed)
        for source in failed_set:
            self._streaks[source] = self._streaks.get(source, 0) + 1
        for source in list(self._streaks):
            if source not in failed_set:
                del self._streaks[source]

        persistently_failed = {s for s, count in self._streaks.items() if count >= FAILURE_THRESHOLD}
        if persistently_failed and persistently_failed != self._last_notified:
            await async_notify_failed_sources(hass, entry, sorted(persistently_failed))
        elif not persistently_failed and self._last_notified:
            await async_dismiss_failed_sources(hass, entry)
        self._last_notified = persistently_failed


class ActivitySensorCoordinator(DataUpdateCoordinator):
    """Polls the configured sources and applies the shared filter rule."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=f"cal_activity_{entry.entry_id}", update_interval=SCAN_INTERVAL
        )
        self.entry = entry
        self._failure_tracker = FailureStreakTracker()

    async def _async_update_data(self):
        sources: list[str] = self.entry.data.get(CONF_SOURCES, [])
        rule = self.entry.data.get(CONF_FILTER)

        now = dt_util.now()
        events, failed = await fetch_matching_events(
            self.hass, sources, rule, now - timedelta(hours=1), now + timedelta(days=30)
        )

        await self._failure_tracker.async_update(self.hass, self.entry, failed)

        return {"events": events, "failed": failed}


async def async_get_or_create_coordinator(
    hass: HomeAssistant, entry: ConfigEntry
) -> ActivitySensorCoordinator:
    """One coordinator per entry, shared between the binary_sensor and sensor platforms."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    key = f"{entry.entry_id}_coordinator"
    coordinator = domain_data.get(key)
    if coordinator is None:
        coordinator = ActivitySensorCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        domain_data[key] = coordinator
    return coordinator
