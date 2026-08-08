"""Diagnostics support for Cal Activity Sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .activity import ActivitySensorCoordinator, event_is_active, event_is_today
from .const import CONF_FILTER, CONF_NAME, CONF_PICTURE, DOMAIN

TO_REDACT = {CONF_NAME, CONF_PICTURE, CONF_FILTER}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Event summaries/descriptions/locations are left out entirely - they're
    calendar content, not integration state, and often personal.
    """
    coordinator: ActivitySensorCoordinator | None = hass.data.get(DOMAIN, {}).get(
        f"{entry.entry_id}_coordinator"
    )

    data: dict[str, Any] = {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
    }

    if coordinator is None:
        data["coordinator"] = "not_initialized"
        return data

    now = dt_util.now()
    events = (coordinator.data or {}).get("events", [])
    failed = (coordinator.data or {}).get("failed", [])

    data["coordinator"] = {
        "last_update_success": coordinator.last_update_success,
        "last_exception": repr(coordinator.last_exception) if coordinator.last_exception else None,
        "update_interval": str(coordinator.update_interval),
        "failed_sources": failed,
        "event_count": len(events),
        "active_event_count": sum(1 for e in events if event_is_active(e, now)),
        "today_event_count": sum(1 for e in events if event_is_today(e, now)),
    }

    return data
