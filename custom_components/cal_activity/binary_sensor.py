"""Binary sensor platform for Cal Activity Sensors."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .activity import (
    ActivitySensorCoordinator,
    async_get_or_create_coordinator,
    event_is_active,
    event_is_today,
    event_is_upcoming,
)
from .const import (
    CONF_CREATE_BINARY,
    CONF_ICON,
    CONF_KIND,
    CONF_NAME,
    CONF_PICTURE,
    CONF_TRIGGER_MODE,
    DEFAULT_ACTIVITY_ICON,
    DEFAULT_COUNTDOWN_ICON,
    KIND_COUNTDOWN,
    TRIGGER_MODE_TODAY,
)
from .life_event import LifeEventCoordinator, async_get_or_create_life_event_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if not entry.data.get(CONF_CREATE_BINARY, True):
        return

    if entry.data.get(CONF_KIND) == KIND_COUNTDOWN:
        coordinator = await async_get_or_create_life_event_coordinator(hass, entry)
        async_add_entities([CountdownBinarySensor(coordinator, entry)])
        return

    coordinator = await async_get_or_create_coordinator(hass, entry)
    async_add_entities([ActivityBinarySensor(coordinator, entry)])


class ActivityBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """On when at least one matching event is happening right now."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ActivitySensorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_name = entry.data.get(CONF_NAME, "Aktivitet")

    @property
    def icon(self) -> str:
        return self._entry.data.get(CONF_ICON) or DEFAULT_ACTIVITY_ICON

    @property
    def entity_picture(self) -> str | None:
        return self._entry.data.get(CONF_PICTURE) or None

    @property
    def is_on(self) -> bool:
        now = dt_util.now()
        events = (self.coordinator.data or {}).get("events", [])
        if self._entry.data.get(CONF_TRIGGER_MODE) == TRIGGER_MODE_TODAY:
            return any(event_is_today(e, now) for e in events)
        return any(event_is_active(e, now) for e in events)

    @property
    def extra_state_attributes(self) -> dict:
        now = dt_util.now()
        events = (self.coordinator.data or {}).get("events", [])
        active = [e for e in events if event_is_active(e, now)]
        upcoming = sorted([e for e in events if event_is_upcoming(e, now)], key=lambda e: str(e.start))

        attrs: dict = {}
        if active:
            attrs["current_event"] = active[0].summary
        if upcoming:
            attrs["next_event"] = upcoming[0].summary
            attrs["next_start"] = (
                upcoming[0].start.isoformat()
                if hasattr(upcoming[0].start, "isoformat")
                else str(upcoming[0].start)
            )
        failed = (self.coordinator.data or {}).get("failed") or []
        if failed:
            attrs["failed_sources"] = failed
        return attrs


class CountdownBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """On for the whole span - the single configured day, or every day of a
    multi-day span (e.g. a trip) - not just its first day."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LifeEventCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_countdown_today"
        self._attr_name = entry.data.get(CONF_NAME, "Nedräkning")

    @property
    def icon(self) -> str:
        return self._entry.data.get(CONF_ICON) or DEFAULT_COUNTDOWN_ICON

    @property
    def entity_picture(self) -> str | None:
        return self._entry.data.get(CONF_PICTURE) or None

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data or {}).get("is_current"))

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        attrs: dict = {}
        next_date = data.get("next_date")
        if next_date:
            attrs["next_date"] = next_date.isoformat()
        if data.get("label"):
            attrs["label"] = data["label"]
        if data.get("years") is not None:
            attrs["years"] = data["years"]
        span_length = data.get("span_length")
        if span_length and span_length > 1:
            attrs["end_date"] = data["end_date"].isoformat()
            attrs["span_length"] = span_length
            if data.get("day_of_span") is not None:
                attrs["day_of_span"] = data["day_of_span"]
        failed = data.get("failed") or []
        if failed:
            attrs["failed_sources"] = failed
        return attrs
