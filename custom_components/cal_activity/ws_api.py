"""Websocket API used by the Cal Activity Sensors sidebar panel."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .activity_log import async_clear, async_get_entries, async_log
from .const import (
    CONF_CREATE_BINARY,
    CONF_CREATE_SENSOR,
    CONF_DATE,
    CONF_DATE_SOURCE,
    CONF_FILTER,
    CONF_ICON,
    CONF_KIND,
    CONF_NAME,
    CONF_PICTURE,
    CONF_RECURRING,
    CONF_SOURCES,
    CONF_TRIGGER_MODE,
    DATE_SOURCE_CALENDAR,
    DATE_SOURCE_MANUAL,
    DOMAIN,
    KIND_ACTIVITY,
    KIND_COUNTDOWN,
    TRIGGER_MODE_ACTIVE,
)


def _entry_to_dict(entry) -> dict:
    kind = entry.data.get(CONF_KIND, KIND_ACTIVITY)
    result = {
        "entry_id": entry.entry_id,
        "kind": kind,
        "name": entry.data.get(CONF_NAME),
        "sources": entry.data.get(CONF_SOURCES, []),
        "icon": entry.data.get(CONF_ICON),
        "picture": entry.data.get(CONF_PICTURE),
        "filter": entry.data.get(CONF_FILTER),
        "create_binary_sensor": entry.data.get(CONF_CREATE_BINARY, True),
        "create_sensor": entry.data.get(CONF_CREATE_SENSOR, True),
    }
    if kind == KIND_COUNTDOWN:
        result["date_source"] = entry.data.get(CONF_DATE_SOURCE, DATE_SOURCE_MANUAL)
        result["date"] = entry.data.get(CONF_DATE)
        result["recurring"] = entry.data.get(CONF_RECURRING, True)
    else:
        result["trigger_mode"] = entry.data.get(CONF_TRIGGER_MODE, TRIGGER_MODE_ACTIVE)
    return result


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_entries"})
@websocket_api.async_response
async def ws_list_entries(hass: HomeAssistant, connection, msg):
    entries = hass.config_entries.async_entries(DOMAIN)
    connection.send_result(msg["id"], {"entries": [_entry_to_dict(e) for e in entries]})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_calendars"})
@websocket_api.async_response
async def ws_list_calendars(hass: HomeAssistant, connection, msg):
    calendars = [
        {"entity_id": state.entity_id, "name": state.attributes.get("friendly_name", state.entity_id)}
        for state in hass.states.async_all("calendar")
    ]
    calendars.sort(key=lambda c: c["name"])
    connection.send_result(msg["id"], {"calendars": calendars})


def _validate_kind_fields(connection, msg_id, msg) -> bool:
    """Shared create/update validation. Returns False (after sending an error) if invalid."""
    kind = msg.get("kind", KIND_ACTIVITY)
    if kind == KIND_COUNTDOWN:
        date_source = msg.get("date_source", DATE_SOURCE_MANUAL)
        if date_source == DATE_SOURCE_MANUAL and not msg.get("date"):
            connection.send_error(msg_id, "no_date", "Ange ett datum")
            return False
        if date_source == DATE_SOURCE_CALENDAR and not msg["sources"]:
            connection.send_error(msg_id, "no_sources", "Välj minst en källkalender")
            return False
    elif not msg["sources"]:
        connection.send_error(msg_id, "no_sources", "Välj minst en källkalender")
        return False
    if not (msg["create_binary_sensor"] or msg["create_sensor"]):
        connection.send_error(msg_id, "no_sensor_type", "Välj minst en sensor-typ")
        return False
    return True


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/create_entry",
        vol.Required("name"): str,
        vol.Required("sources"): [str],
        vol.Optional("icon"): vol.Any(str, None),
        vol.Optional("picture"): vol.Any(str, None),
        vol.Optional("field", default="any"): str,
        vol.Optional("include", default=""): str,
        vol.Optional("exclude", default=""): str,
        vol.Optional("use_regex", default=False): bool,
        vol.Optional("case_sensitive", default=False): bool,
        vol.Optional("trigger_mode", default=TRIGGER_MODE_ACTIVE): str,
        vol.Optional("create_binary_sensor", default=True): bool,
        vol.Optional("create_sensor", default=True): bool,
        vol.Optional("kind", default=KIND_ACTIVITY): str,
        vol.Optional("date_source", default=DATE_SOURCE_MANUAL): str,
        vol.Optional("date"): vol.Any(str, None),
        vol.Optional("recurring", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_create_entry(hass: HomeAssistant, connection, msg):
    if not _validate_kind_fields(connection, msg["id"], msg):
        return

    payload = {k: v for k, v in msg.items() if k != "type"}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "create"}, data=payload)
    if result.get("type") == "form":
        connection.send_error(msg["id"], "invalid_input", "Kunde inte skapa sensorn")
        return
    entry_id = result["result"].entry_id
    await async_log(hass, entry_id, "Sensor skapad")
    connection.send_result(msg["id"], {"ok": True, "entry_id": entry_id})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/update_entry",
        vol.Required("entry_id"): str,
        vol.Required("name"): str,
        vol.Required("sources"): [str],
        vol.Optional("icon"): vol.Any(str, None),
        vol.Optional("picture"): vol.Any(str, None),
        vol.Optional("field", default="any"): str,
        vol.Optional("include", default=""): str,
        vol.Optional("exclude", default=""): str,
        vol.Optional("use_regex", default=False): bool,
        vol.Optional("case_sensitive", default=False): bool,
        vol.Optional("trigger_mode", default=TRIGGER_MODE_ACTIVE): str,
        vol.Optional("create_binary_sensor", default=True): bool,
        vol.Optional("create_sensor", default=True): bool,
        vol.Optional("kind", default=KIND_ACTIVITY): str,
        vol.Optional("date_source", default=DATE_SOURCE_MANUAL): str,
        vol.Optional("date"): vol.Any(str, None),
        vol.Optional("recurring", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_update_entry(hass: HomeAssistant, connection, msg):
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "not_found", "Hittade inte sensorn")
        return
    if not _validate_kind_fields(connection, msg["id"], msg):
        return

    include = [w.strip() for w in msg["include"].split(",") if w.strip()]
    exclude = [w.strip() for w in msg["exclude"].split(",") if w.strip()]
    rule = (
        {
            "field": msg["field"],
            "include": include,
            "exclude": exclude,
            "use_regex": msg["use_regex"],
            "case_sensitive": msg["case_sensitive"],
        }
        if (include or exclude)
        else None
    )
    kind = msg.get("kind", KIND_ACTIVITY)

    changes = []
    if msg["name"] != entry.data.get(CONF_NAME):
        changes.append(f'namn ändrat till "{msg["name"]}"')
    if set(msg["sources"]) != set(entry.data.get(CONF_SOURCES, [])):
        changes.append("källor uppdaterade")
    if rule != entry.data.get(CONF_FILTER):
        changes.append("filter uppdaterat")
    if kind == KIND_ACTIVITY and msg["trigger_mode"] != entry.data.get(
        CONF_TRIGGER_MODE, TRIGGER_MODE_ACTIVE
    ):
        changes.append("triggerläge ändrat")
    if kind == KIND_COUNTDOWN and msg.get("date") != entry.data.get(CONF_DATE):
        changes.append("datum ändrat")
    if kind == KIND_COUNTDOWN and msg.get("recurring", True) != entry.data.get(CONF_RECURRING, True):
        changes.append("återkommande ändrat")
    if msg.get("icon") != entry.data.get(CONF_ICON):
        changes.append("ikon ändrad")
    if msg.get("picture") != entry.data.get(CONF_PICTURE):
        changes.append("bild ändrad")

    new_data = dict(entry.data)
    new_data[CONF_KIND] = kind
    new_data[CONF_NAME] = msg["name"]
    new_data[CONF_SOURCES] = msg["sources"]
    new_data[CONF_ICON] = msg.get("icon")
    new_data[CONF_PICTURE] = msg.get("picture")
    new_data[CONF_FILTER] = rule
    new_data[CONF_CREATE_BINARY] = msg["create_binary_sensor"]
    new_data[CONF_CREATE_SENSOR] = msg["create_sensor"]
    if kind == KIND_COUNTDOWN:
        new_data[CONF_DATE_SOURCE] = msg.get("date_source", DATE_SOURCE_MANUAL)
        new_data[CONF_DATE] = msg.get("date") or None
        new_data[CONF_RECURRING] = msg.get("recurring", True)
    else:
        new_data[CONF_TRIGGER_MODE] = msg["trigger_mode"]
    hass.config_entries.async_update_entry(entry, data=new_data, title=msg["name"])
    await hass.config_entries.async_reload(entry.entry_id)
    if changes:
        await async_log(hass, entry.entry_id, "Uppdaterad: " + "; ".join(changes))
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/delete_entry", vol.Required("entry_id"): str}
)
@websocket_api.async_response
async def ws_delete_entry(hass: HomeAssistant, connection, msg):
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "not_found", "Hittade inte sensorn")
        return
    await hass.config_entries.async_remove(msg["entry_id"])
    await async_clear(hass, msg["entry_id"])
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/get_activity_log", vol.Required("entry_id"): str}
)
@websocket_api.async_response
async def ws_get_activity_log(hass: HomeAssistant, connection, msg):
    entries = await async_get_entries(hass, msg["entry_id"])
    connection.send_result(msg["id"], {"entries": entries})


def async_register_ws_api(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_list_entries)
    websocket_api.async_register_command(hass, ws_list_calendars)
    websocket_api.async_register_command(hass, ws_create_entry)
    websocket_api.async_register_command(hass, ws_update_entry)
    websocket_api.async_register_command(hass, ws_delete_entry)
    websocket_api.async_register_command(hass, ws_get_activity_log)
