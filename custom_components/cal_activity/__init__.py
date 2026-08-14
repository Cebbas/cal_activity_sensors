"""The Cal Activity Sensors integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .panel import async_register_panel
from .ws_api import async_register_ws_api

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async_register_ws_api(hass)
    await async_register_panel(hass)
    return True


def _remove_orphaned_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Self-healing cleanup for entity-platform changes across releases.

    Toggling a sensor type off (back when binary_sensor/sensor were both
    separately creatable), and later switching which platform is used for
    the single entity (sensor -> binary_sensor), both leave a stale
    entity-registry entry behind: HA doesn't purge a unique_id's registry
    entry just because a reload stops returning it, only when the whole
    config entry is removed. Sweep away anything not in the domain(s) this
    version of the integration actually uses, every setup, so nobody has to
    find and delete leftovers by hand in Settings > Entities.
    """
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        domain = reg_entry.entity_id.split(".", 1)[0]
        if domain not in PLATFORMS:
            registry.async_remove(reg_entry.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"entry": entry}

    _remove_orphaned_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_coordinator", None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_life_coordinator", None)
    return unload_ok
