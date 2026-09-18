"""Constants for Cal Activity Sensors."""

DOMAIN = "cal_activity"

CONF_NAME = "name"
CONF_SOURCES = "sources"
CONF_ICON = "icon"
CONF_PICTURE = "picture"
CONF_FILTER = "filter"
CONF_TRIGGER_MODE = "trigger_mode"
TRIGGER_MODE_ACTIVE = "active_now"
TRIGGER_MODE_TODAY = "today"
TRIGGER_MODES = [TRIGGER_MODE_ACTIVE, TRIGGER_MODE_TODAY]

FILTER_FIELDS = ["any", "summary", "description", "location"]

DEFAULT_ACTIVITY_ICON = "mdi:calendar-check"

CONF_KIND = "kind"
KIND_ACTIVITY = "activity"
KIND_COUNTDOWN = "countdown"
KIND_BIRTHDAY = "birthday"
KINDS = [KIND_ACTIVITY, KIND_COUNTDOWN, KIND_BIRTHDAY]

# Optional link to a person entity, birthday-kind only ("advanced option" -
# only shown to users with Advanced Mode enabled, see config_flow.py).
CONF_PERSON = "person_entity"

CONF_DATE_SOURCE = "date_source"
DATE_SOURCE_MANUAL = "manual"
DATE_SOURCE_CALENDAR = "calendar"
DATE_SOURCES = [DATE_SOURCE_MANUAL, DATE_SOURCE_CALENDAR]

CONF_DATE = "date"
CONF_DATE_END = "date_end"
CONF_RECURRING = "recurring"

DEFAULT_COUNTDOWN_ICON = "mdi:calendar-star"
DEFAULT_BIRTHDAY_ICON = "mdi:cake-variant"

PLATFORMS = ["binary_sensor"]
