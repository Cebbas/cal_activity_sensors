"""Config flow for Cal Activity Sensors."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CREATE_BINARY,
    CONF_CREATE_SENSOR,
    CONF_FILTER,
    CONF_ICON,
    CONF_NAME,
    CONF_PICTURE,
    CONF_SOURCES,
    CONF_TRIGGER_MODE,
    DOMAIN,
    FILTER_FIELDS,
    TRIGGER_MODE_ACTIVE,
    TRIGGER_MODES,
)


def _build_filter_from_flat_input(user_input: dict) -> dict | None:
    include = [w.strip() for w in user_input.get("include", "").split(",") if w.strip()]
    exclude = [w.strip() for w in user_input.get("exclude", "").split(",") if w.strip()]
    if not include and not exclude:
        return None
    return {
        "field": user_input.get("field", "any"),
        "include": include,
        "exclude": exclude,
        "use_regex": user_input.get("use_regex", False),
        "case_sensitive": user_input.get("case_sensitive", False),
    }


def _icon_and_picture_fields(defaults: dict) -> dict:
    return {
        vol.Optional(CONF_ICON, default=defaults.get(CONF_ICON, "")): selector.IconSelector(),
        vol.Optional(CONF_PICTURE, default=defaults.get(CONF_PICTURE, "")): selector.TextSelector(),
    }


def _activity_sensor_schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    rule = defaults.get(CONF_FILTER) or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Aktivitet")): str,
            vol.Required(
                CONF_SOURCES, default=defaults.get(CONF_SOURCES, [])
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar", multiple=True)
            ),
            **_icon_and_picture_fields(defaults),
            vol.Optional("field", default=rule.get("field", "any")): vol.In(FILTER_FIELDS),
            vol.Optional("include", default=", ".join(rule.get("include", []))): str,
            vol.Optional("exclude", default=", ".join(rule.get("exclude", []))): str,
            vol.Optional("use_regex", default=rule.get("use_regex", False)): bool,
            vol.Optional("case_sensitive", default=rule.get("case_sensitive", False)): bool,
            vol.Optional(
                CONF_TRIGGER_MODE, default=defaults.get(CONF_TRIGGER_MODE, TRIGGER_MODE_ACTIVE)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=TRIGGER_MODES,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_TRIGGER_MODE,
                )
            ),
            vol.Optional(
                "create_binary_sensor", default=defaults.get(CONF_CREATE_BINARY, True)
            ): bool,
            vol.Optional("create_sensor", default=defaults.get(CONF_CREATE_SENSOR, True)): bool,
        }
    )


class CalActivityConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Creates an activity sensor."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_SOURCES]:
                errors["sources"] = "no_sources"
            elif not (user_input.get("create_binary_sensor") or user_input.get("create_sensor")):
                errors["create_binary_sensor"] = "no_sensor_type"
            else:
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_SOURCES: user_input[CONF_SOURCES],
                    CONF_ICON: user_input.get(CONF_ICON),
                    CONF_PICTURE: user_input.get(CONF_PICTURE),
                    CONF_FILTER: _build_filter_from_flat_input(user_input),
                    CONF_TRIGGER_MODE: user_input.get(CONF_TRIGGER_MODE, TRIGGER_MODE_ACTIVE),
                    CONF_CREATE_BINARY: user_input["create_binary_sensor"],
                    CONF_CREATE_SENSOR: user_input["create_sensor"],
                }
                return self.async_create_entry(title=user_input[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="user", data_schema=_activity_sensor_schema(), errors=errors
        )

    # Kept as a separate context source (used by the sidebar panel's "create"
    # button) even though it shows the exact same form as async_step_user -
    # having a distinct source lets the panel init the flow without going
    # through the generic "user" entry point HA's own UI also uses.
    async def async_step_create(self, user_input=None):
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CalActivityOptionsFlow()


class CalActivityOptionsFlow(config_entries.OptionsFlow):
    """Edit an existing activity sensor."""

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        current = self.config_entry.data

        if user_input is not None:
            if not user_input[CONF_SOURCES]:
                errors["sources"] = "no_sources"
            elif not (user_input.get("create_binary_sensor") or user_input.get("create_sensor")):
                errors["create_binary_sensor"] = "no_sensor_type"
            else:
                new_data = dict(current)
                new_data[CONF_NAME] = user_input[CONF_NAME]
                new_data[CONF_SOURCES] = user_input[CONF_SOURCES]
                new_data[CONF_ICON] = user_input.get(CONF_ICON)
                new_data[CONF_PICTURE] = user_input.get(CONF_PICTURE)
                new_data[CONF_FILTER] = _build_filter_from_flat_input(user_input)
                new_data[CONF_TRIGGER_MODE] = user_input.get(CONF_TRIGGER_MODE, TRIGGER_MODE_ACTIVE)
                new_data[CONF_CREATE_BINARY] = user_input["create_binary_sensor"]
                new_data[CONF_CREATE_SENSOR] = user_input["create_sensor"]
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data, title=user_input[CONF_NAME]
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_activity_sensor_schema(current),
            errors=errors,
        )
