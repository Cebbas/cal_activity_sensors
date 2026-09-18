"""Mirrors a birthday's current yearly occurrence into a target calendar.

`calendar.create_event` doesn't reliably return a usable event UID across
every calendar platform (Local Calendar, CalDAV, Google, ...), so this
can't safely delete-and-recreate an event when the date changes - and there
is no generic "update event" service to begin with. Instead, this just
creates one plain (non-recurring) all-day event per occurrence and tracks
which occurrence was last synced (per config entry, in its own small
`Store` - deliberately not in the config entry's own `data`, since writing
that would fire this integration's own update-listener and reload the
entry it's running inside of). The date naturally advances to next year's
occurrence on the next poll after the birthday passes, so re-sync happens
on its own without needing calendar-side recurrence support at all.

Trade-off: switching the target calendar, or deleting the birthday sensor,
leaves any already-created event(s) behind in the old calendar - nothing
here can reliably clean those up. Documented in IDEAS.md/README.md.
"""
from __future__ import annotations

from datetime import date, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


def _store(hass: HomeAssistant, entry_id: str) -> Store:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}_calendar_sync_{entry_id}")


async def async_sync_birthday_occurrence(
    hass: HomeAssistant,
    entry: ConfigEntry,
    target_calendar: str,
    name: str,
    start: date,
    end_inclusive: date,
) -> None:
    """Create this year's (or whichever is current) calendar event for a
    birthday, once - a no-op if this exact occurrence was already synced to
    this exact calendar."""
    store = _store(hass, entry.entry_id)
    synced = await store.async_load() or {}
    sync_key = f"{target_calendar}:{start.isoformat()}"
    if synced.get("sync_key") == sync_key:
        return

    try:
        await hass.services.async_call(
            "calendar",
            "create_event",
            {
                "entity_id": target_calendar,
                "summary": name,
                "start_date": start.isoformat(),
                # Calendar `end_date` is exclusive for all-day events (same
                # convention this integration already normalizes to
                # elsewhere - see activity.py/life_event.py's own handling
                # of calendar all-day start/end).
                "end_date": (end_inclusive + timedelta(days=1)).isoformat(),
            },
            blocking=True,
        )
    except Exception as err:  # noqa: BLE001 - don't take the sensor update down with it
        _LOGGER.warning(
            "Could not create calendar event for %s in %s: %s", name, target_calendar, err
        )
        return

    await store.async_save({"sync_key": sync_key})


async def async_clear(hass: HomeAssistant, entry_id: str) -> None:
    """Drop the sync-state store for a removed entry (doesn't touch any
    event already created in the target calendar - see module docstring)."""
    await _store(hass, entry_id).async_remove()
