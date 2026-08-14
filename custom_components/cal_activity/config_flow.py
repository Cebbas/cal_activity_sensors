"""Config flow for Cal Activity Sensors."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CREATE_BINARY,
    CONF_CREATE_SENSOR,
    CONF_DATE,
    CONF_DATE_END,
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
    DATE_SOURCES,
    DOMAIN,
    FILTER_FIELDS,
    KIND_ACTIVITY,
    KIND_COUNTDOWN,
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


def _sensor_type_fields(defaults: dict) -> dict:
    return {
        vol.Optional(
            "create_binary_sensor", default=defaults.get(CONF_CREATE_BINARY, True)
        ): bool,
        vol.Optional("create_sensor", default=defaults.get(CONF_CREATE_SENSOR, True)): bool,
    }


def _filter_fields(rule: dict) -> dict:
    return {
        vol.Optional("field", default=rule.get("field", "any")): vol.In(FILTER_FIELDS),
        vol.Optional("include", default=", ".join(rule.get("include", []))): str,
        vol.Optional("exclude", default=", ".join(rule.get("exclude", []))): str,
        vol.Optional("use_regex", default=rule.get("use_regex", False)): bool,
        vol.Optional("case_sensitive", default=rule.get("case_sensitive", False)): bool,
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
            **_filter_fields(rule),
            vol.Optional(
                CONF_TRIGGER_MODE, default=defaults.get(CONF_TRIGGER_MODE, TRIGGER_MODE_ACTIVE)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=TRIGGER_MODES,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_TRIGGER_MODE,
                )
            ),
            **_sensor_type_fields(defaults),
        }
    )


def _countdown_sensor_schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    rule = defaults.get(CONF_FILTER) or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Livshändelse")): str,
            **_icon_and_picture_fields(defaults),
            vol.Optional(
                CONF_DATE_SOURCE, default=defaults.get(CONF_DATE_SOURCE, DATE_SOURCE_MANUAL)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=DATE_SOURCES,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_DATE_SOURCE,
                )
            ),
            # Plain text (not a DateSelector) so it can stay empty when the
            # source is "calendar" instead - a DateSelector would reject an
            # empty value even though the field isn't used in that mode.
            vol.Optional(CONF_DATE, default=defaults.get(CONF_DATE) or ""): str,
            # Optional - only set for a multi-day span (e.g. a trip). Empty
            # means a single-day date, same as leaving it out entirely.
            vol.Optional(CONF_DATE_END, default=defaults.get(CONF_DATE_END) or ""): str,
            vol.Optional(CONF_RECURRING, default=defaults.get(CONF_RECURRING, True)): bool,
            vol.Optional(
                CONF_SOURCES, default=defaults.get(CONF_SOURCES, [])
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar", multiple=True)
            ),
            **_filter_fields(rule),
            **_sensor_type_fields(defaults),
        }
    )


def _countdown_data_from_input(user_input: dict) -> dict:
    return {
        CONF_KIND: KIND_COUNTDOWN,
        CONF_NAME: user_input[CONF_NAME],
        CONF_ICON: user_input.get(CONF_ICON),
        CONF_PICTURE: user_input.get(CONF_PICTURE),
        CONF_DATE_SOURCE: user_input.get(CONF_DATE_SOURCE, DATE_SOURCE_MANUAL),
        CONF_DATE: user_input.get(CONF_DATE) or None,
        CONF_DATE_END: user_input.get(CONF_DATE_END) or None,
        CONF_RECURRING: user_input.get(CONF_RECURRING, True),
        CONF_SOURCES: user_input.get(CONF_SOURCES, []),
        CONF_FILTER: _build_filter_from_flat_input(user_input),
        CONF_CREATE_BINARY: user_input["create_binary_sensor"],
        CONF_CREATE_SENSOR: user_input["create_sensor"],
    }


def _countdown_errors(user_input: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    date_source = user_input.get(CONF_DATE_SOURCE, DATE_SOURCE_MANUAL)
    if date_source == DATE_SOURCE_MANUAL and not user_input.get(CONF_DATE):
        errors["date"] = "no_date"
    elif (
        date_source == DATE_SOURCE_MANUAL
        and user_input.get(CONF_DATE_END)
        and user_input[CONF_DATE_END] < user_input[CONF_DATE]
    ):
        errors["date_end"] = "end_before_start"
    elif date_source == DATE_SOURCE_CALENDAR and not user_input.get(CONF_SOURCES):
        errors["sources"] = "no_sources"
    elif not (user_input.get("create_binary_sensor") or user_input.get("create_sensor")):
        errors["create_binary_sensor"] = "no_sensor_type"
    return errors


class CalActivityConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Creates an activity or countdown/life-event sensor."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["activity", "countdown"])

    async def async_step_activity(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_SOURCES]:
                errors["sources"] = "no_sources"
            elif not (user_input.get("create_binary_sensor") or user_input.get("create_sensor")):
                errors["create_binary_sensor"] = "no_sensor_type"
            else:
                data = {
                    CONF_KIND: KIND_ACTIVITY,
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
            step_id="activity", data_schema=_activity_sensor_schema(), errors=errors
        )

    async def async_step_countdown(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _countdown_errors(user_input)
            if not errors:
                data = _countdown_data_from_input(user_input)
                return self.async_create_entry(title=user_input[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="countdown", data_schema=_countdown_sensor_schema(), errors=errors
        )

    # Kept as a separate context source (used by the sidebar panel's "create"
    # button) even though it shows the exact same forms as the interactive
    # menu-driven steps - having a distinct source lets the panel init the
    # flow with a full flat payload (including `kind`) and skip straight to
    # creation, instead of going through the "user" menu HA's own UI shows.
    async def async_step_create(self, user_input=None):
        kind = (user_input or {}).get(CONF_KIND, KIND_ACTIVITY)
        if kind == KIND_COUNTDOWN:
            return await self.async_step_countdown(user_input)
        return await self.async_step_activity(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CalActivityOptionsFlow()


class CalActivityOptionsFlow(config_entries.OptionsFlow):
    """Edit an existing activity or countdown/life-event sensor."""

    async def async_step_init(self, user_input=None):
        current = self.config_entry.data
        if current.get(CONF_KIND) == KIND_COUNTDOWN:
            return await self._async_step_countdown(user_input)
        return await self._async_step_activity(user_input)

    async def _async_step_activity(self, user_input=None):
        errors: dict[str, str] = {}
        current = self.config_entry.data

        if user_input is not None:
            if not user_input[CONF_SOURCES]:
                errors["sources"] = "no_sources"
            elif not (user_input.get("create_binary_sensor") or user_input.get("create_sensor")):
                errors["create_binary_sensor"] = "no_sensor_type"
            else:
                new_data = dict(current)
                new_data[CONF_KIND] = KIND_ACTIVITY
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

    async def _async_step_countdown(self, user_input=None):
        errors: dict[str, str] = {}
        current = self.config_entry.data

        if user_input is not None:
            errors = _countdown_errors(user_input)
            if not errors:
                new_data = dict(current)
                new_data.update(_countdown_data_from_input(user_input))
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data, title=user_input[CONF_NAME]
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_countdown_sensor_schema(current),
            errors=errors,
        )
