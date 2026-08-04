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

PLATFORMS = ["binary_sensor", "sensor"]
