"""Constants for Cal Activity Sensors."""

DOMAIN = "cal_activity"

CONF_NAME = "name"
CONF_SOURCES = "sources"
CONF_ICON = "icon"
CONF_PICTURE = "picture"
CONF_FILTER = "filter"
CONF_CREATE_BINARY = "create_binary_sensor"
CONF_CREATE_SENSOR = "create_sensor"
CONF_TRIGGER_MODE = "trigger_mode"
TRIGGER_MODE_ACTIVE = "active_now"
TRIGGER_MODE_TODAY = "today"
TRIGGER_MODES = [TRIGGER_MODE_ACTIVE, TRIGGER_MODE_TODAY]

FILTER_FIELDS = ["any", "summary", "description", "location"]

DEFAULT_ACTIVITY_ICON = "mdi:calendar-check"

CONF_KIND = "kind"
KIND_ACTIVITY = "activity"
KIND_COUNTDOWN = "countdown"
KINDS = [KIND_ACTIVITY, KIND_COUNTDOWN]

CONF_DATE_SOURCE = "date_source"
DATE_SOURCE_MANUAL = "manual"
DATE_SOURCE_CALENDAR = "calendar"
DATE_SOURCES = [DATE_SOURCE_MANUAL, DATE_SOURCE_CALENDAR]

CONF_DATE = "date"
CONF_RECURRING = "recurring"

DEFAULT_COUNTDOWN_ICON = "mdi:calendar-star"

PLATFORMS = ["binary_sensor", "sensor"]
