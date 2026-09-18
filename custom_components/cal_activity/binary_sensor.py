"""Binary sensor platform for Cal Activity Sensors.

The single entity per config entry - state is native on/off ("active" or
not), with everything else (which event, next date, days remaining, ...) as
attributes. A plain `sensor` can't express on/off as its actual state without
resorting to string literals, so this is genuinely a binary_sensor rather
than a sensor with an `active` attribute.
"""
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
    event_sort_key,
)
from .const import (
    CONF_ICON,
    CONF_KIND,
    CONF_NAME,
    CONF_PERSON,
    CONF_PICTURE,
    CONF_TRIGGER_MODE,
    DEFAULT_ACTIVITY_ICON,
    DEFAULT_BIRTHDAY_ICON,
    DEFAULT_COUNTDOWN_ICON,
    KIND_BIRTHDAY,
    KIND_COUNTDOWN,
    TRIGGER_MODE_TODAY,
)
from .life_event import LifeEventCoordinator, async_get_or_create_life_event_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    kind = entry.data.get(CONF_KIND)
    if kind in (KIND_COUNTDOWN, KIND_BIRTHDAY):
        coordinator = await async_get_or_create_life_event_coordinator(hass, entry)
        sensor_cls = BirthdayBinarySensor if kind == KIND_BIRTHDAY else CountdownBinarySensor
        async_add_entities([sensor_cls(coordinator, entry)])
        return

    coordinator = await async_get_or_create_coordinator(hass, entry)
    async_add_entities([ActivityBinarySensor(coordinator, entry)])


class ActivityBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """On per the configured trigger_mode ("pågår just nu" or "inträffar idag")."""

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
        upcoming = sorted([e for e in events if event_is_upcoming(e, now)], key=event_sort_key)
        today_count = sum(1 for e in events if event_is_today(e, now))

        attrs: dict = {"matches_today": today_count}
        if active:
            attrs["current_event"] = active[0].summary
            if self._entry.data.get(CONF_TRIGGER_MODE) != TRIGGER_MODE_TODAY:
                end = active[0].end
                attrs["active_until"] = end.isoformat() if hasattr(end, "isoformat") else str(end)
        if upcoming:
            next_event = upcoming[0]
            attrs["next_event"] = next_event.summary
            attrs["next_start"] = (
                next_event.start.isoformat() if hasattr(next_event.start, "isoformat") else str(next_event.start)
            )
            attrs["next_end"] = (
                next_event.end.isoformat() if hasattr(next_event.end, "isoformat") else str(next_event.end)
            )
            if next_event.location:
                attrs["location"] = next_event.location
        failed = (self.coordinator.data or {}).get("failed") or []
        if failed:
            attrs["failed_sources"] = failed
        return attrs


class CountdownBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """On for every day of the span - the single configured day, or every day
    of a multi-day span like a trip, not just its first day."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LifeEventCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_countdown"
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
        passed = bool(data.get("passed"))
        phase = "in_progress" if data.get("is_current") else ("passed" if passed else "upcoming")

        attrs: dict = {"phase": phase}
        days_remaining = data.get("days_remaining")
        if days_remaining is not None:
            attrs["days_remaining"] = days_remaining
        next_date = data.get("next_date")
        if next_date:
            attrs["next_date"] = next_date.isoformat()
            today = dt_util.now().date()
            attrs["days_until_start"] = (next_date - today).days
        if data.get("label"):
            attrs["label"] = data["label"]
        if data.get("years") is not None:
            attrs["years"] = data["years"]
        if passed:
            attrs["passed"] = True
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


class BirthdayBinarySensor(CountdownBinarySensor):
    """A birthday is the same single-day, always-recurring date math as
    CountdownBinarySensor - kept as a thin subclass (not a duplicated
    coordinator/entity) rather than a fully separate implementation, and
    deliberately keeps the same unique_id suffix as its parent so a
    countdown entry migrated to this kind keeps its existing entity_id and
    history instead of becoming a new, orphaned entity.

    Its own kind mainly exists so the config flow can offer a focused
    two-field form (name + date) instead of every countdown option, and so
    the panel/UI can treat it as its own category.
    """

    @property
    def icon(self) -> str:
        return self._entry.data.get(CONF_ICON) or DEFAULT_BIRTHDAY_ICON

    @property
    def entity_picture(self) -> str | None:
        picture = self._entry.data.get(CONF_PICTURE)
        if picture:
            return picture
        person = self._entry.data.get(CONF_PERSON)
        if person:
            person_state = self.hass.states.get(person)
            if person_state:
                return person_state.attributes.get("entity_picture")
        return None

    @property
    def extra_state_attributes(self) -> dict:
        attrs = dict(super().extra_state_attributes)
        if attrs.get("years") is not None:
            attrs["age"] = attrs["years"]
        person = self._entry.data.get(CONF_PERSON)
        if person:
            attrs["person"] = person
        return attrs
