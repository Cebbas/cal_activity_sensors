"""Tests for the Birthday kind: the migration helper in __init__.py and
BirthdayBinarySensor's icon/attribute overrides in binary_sensor.py.
"""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cal_activity import _migrate_birthday_named_countdowns
from custom_components.cal_activity.binary_sensor import BirthdayBinarySensor
from custom_components.cal_activity.const import (
    CONF_DATE_SOURCE,
    CONF_KIND,
    CONF_NAME,
    CONF_PERSON,
    CONF_PICTURE,
    DATE_SOURCE_CALENDAR,
    DATE_SOURCE_MANUAL,
    DEFAULT_BIRTHDAY_ICON,
    DOMAIN,
    KIND_BIRTHDAY,
    KIND_COUNTDOWN,
)


class _FakeCoordinator:
    def __init__(self, data):
        self.data = data


def _birthday_sensor(data, person=None, picture=None) -> BirthdayBinarySensor:
    entry_data = {CONF_NAME: "Farmors Födelsedag"}
    if person is not None:
        entry_data[CONF_PERSON] = person
    if picture is not None:
        entry_data[CONF_PICTURE] = picture
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    sensor = BirthdayBinarySensor(_FakeCoordinator(data), entry)
    return sensor


def test_birthday_default_icon_is_cake():
    sensor = _birthday_sensor({"is_current": False, "passed": False})
    assert sensor.icon == DEFAULT_BIRTHDAY_ICON


def test_birthday_age_attribute_mirrors_years():
    sensor = _birthday_sensor({"is_current": False, "passed": False, "years": 42})
    assert sensor.extra_state_attributes["age"] == 42
    assert sensor.extra_state_attributes["years"] == 42


def test_birthday_no_age_attribute_when_years_missing():
    sensor = _birthday_sensor({"is_current": False, "passed": False})
    assert "age" not in sensor.extra_state_attributes


def test_birthday_person_attribute_present_when_linked():
    sensor = _birthday_sensor({"is_current": False, "passed": False}, person="person.naomi")
    assert sensor.extra_state_attributes["person"] == "person.naomi"


def test_birthday_no_person_attribute_when_not_linked():
    sensor = _birthday_sensor({"is_current": False, "passed": False})
    assert "person" not in sensor.extra_state_attributes


async def test_birthday_picture_prefers_own_picture_over_person(hass):
    sensor = _birthday_sensor(
        {"is_current": False, "passed": False}, person="person.naomi", picture="/local/naomi.png"
    )
    sensor.hass = hass
    assert sensor.entity_picture == "/local/naomi.png"


async def test_birthday_picture_falls_back_to_persons_own_picture(hass):
    hass.states.async_set("person.naomi", "home", {"entity_picture": "/api/person/naomi.jpg"})
    sensor = _birthday_sensor({"is_current": False, "passed": False}, person="person.naomi")
    sensor.hass = hass
    assert sensor.entity_picture == "/api/person/naomi.jpg"


async def test_birthday_picture_none_when_no_person_and_no_picture(hass):
    sensor = _birthday_sensor({"is_current": False, "passed": False})
    sensor.hass = hass
    assert sensor.entity_picture is None


async def test_migrate_renames_manual_countdown_with_birthday_in_name(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_KIND: KIND_COUNTDOWN,
            CONF_NAME: "Naomis Födelsedag",
            CONF_DATE_SOURCE: DATE_SOURCE_MANUAL,
        },
    )
    entry.add_to_hass(hass)
    _migrate_birthday_named_countdowns(hass, entry)
    assert entry.data[CONF_KIND] == KIND_BIRTHDAY


async def test_migrate_ignores_non_birthday_countdown(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_KIND: KIND_COUNTDOWN,
            CONF_NAME: "Julafton",
            CONF_DATE_SOURCE: DATE_SOURCE_MANUAL,
        },
    )
    entry.add_to_hass(hass)
    _migrate_birthday_named_countdowns(hass, entry)
    assert entry.data[CONF_KIND] == KIND_COUNTDOWN


async def test_migrate_ignores_calendar_sourced_countdown(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_KIND: KIND_COUNTDOWN,
            CONF_NAME: "Mammas Födelsedag",
            CONF_DATE_SOURCE: DATE_SOURCE_CALENDAR,
        },
    )
    entry.add_to_hass(hass)
    _migrate_birthday_named_countdowns(hass, entry)
    assert entry.data[CONF_KIND] == KIND_COUNTDOWN


async def test_migrate_ignores_activity_kind(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_NAME: "Någons Födelsedag Fest"},
    )
    entry.add_to_hass(hass)
    _migrate_birthday_named_countdowns(hass, entry)
    assert entry.data.get(CONF_KIND) is None
