"""Support for ONVIF binary sensors."""
from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import RestoreSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .base import ONVIFBaseEntity
from .const import DOMAIN
from .device import ONVIFDevice


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a ONVIF binary sensor."""
    device = hass.data[DOMAIN][config_entry.unique_id]

    entities = {
        event.uid: ONVIFSensor(event.uid, device)
        for event in device.events.get_platform("sensor")
    }

    ent_reg = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(ent_reg, config_entry.entry_id):
        if entry.domain == "sensor" and entry.unique_id not in entities:
            entities[entry.unique_id] = ONVIFSensor(entry.unique_id, device, entry)

    async_add_entities(entities.values())

    @callback
    def async_check_entities():
        """Check if we have added an entity for the event."""
        new_entities = []
        for event in device.events.get_platform("sensor"):
            if event.uid not in entities:
                entities[event.uid] = ONVIFSensor(event.uid, device)
                new_entities.append(entities[event.uid])
        async_add_entities(new_entities)

    device.events.async_add_listener(async_check_entities)

    return True


class ONVIFSensor(ONVIFBaseEntity, RestoreSensor):
    """Representation of a ONVIF sensor event."""

    _attr_should_poll = False

    def __init__(self, uid, device: ONVIFDevice, entry: er.RegistryEntry | None = None):
        """Initialize the ONVIF binary sensor."""
        self._attr_unique_id = uid
        if entry is not None:
            self._attr_device_class = entry.original_device_class
            self._attr_entity_category = entry.entity_category
            self._attr_name = entry.name
            self._attr_native_unit_of_measurement = entry.unit_of_measurement
        else:
            event = device.events.get_uid(uid)
            self._attr_device_class = event.device_class
            self._attr_entity_category = event.entity_category
            self._attr_entity_registry_enabled_default = event.entity_enabled
            self._attr_name = f"{device.name} {event.name}"
            self._attr_native_unit_of_measurement = event.unit_of_measurement
            self._attr_native_value = event.value

        super().__init__(device)

    @property
    def native_value(self) -> StateType | date | datetime:
        """Return the value reported by the sensor."""
        if (event := self.device.events.get_uid(self._attr_unique_id)) is not None:
            return event.value
        return self._attr_native_value

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.device.events.async_add_listener(self.async_write_ha_state)
        )
        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last_sensor_data.native_value
