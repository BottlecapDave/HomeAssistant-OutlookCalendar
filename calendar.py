"""Support for Google Calendar Search binary sensors."""
import copy
from datetime import timedelta
import logging

from httplib2 import ServerNotFoundError  # pylint: disable=import-error

from homeassistant.components.calendar import (
    ENTITY_ID_FORMAT,
    CalendarEventDevice,
    calculate_offset,
    is_offset_reached,
    get_date
)
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.util import Throttle, dt

from .const import (
    CONF_CAL_ID,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_IGNORE_AVAILABILITY,
    CONF_MAX_RESULTS,
    CONF_NAME,
    CONF_OFFSET,
    CONF_FILTER,
    CONF_TRACK,
    DEFAULT_CONF_OFFSET,
    TOKEN_FILE,
)

from .client import (
    setup_outh_client,
    OutlookCalendarClient
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_SEARCH_PARAMS = {
    "max_results": 5,
}

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)

def setup_platform(hass, config, add_entities, disc_info=None):
    """Set up the calendar platform for event devices."""
    if disc_info is None:
        return

    if not any(data[CONF_TRACK] for data in disc_info[CONF_ENTITIES]):
        return

    oauth, config_file = setup_outh_client(hass, config)

    calendar_service = OutlookCalendarClient(client=oauth, logger=_LOGGER)
    entities = []
    for data in disc_info[CONF_ENTITIES]:
        if not data[CONF_TRACK]:
            continue
        entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, data[CONF_DEVICE_ID], hass=hass
        )
        entity = OutlookCalendarEventDevice(
            calendar_service, disc_info[CONF_CAL_ID], data, entity_id
        )
        entities.append(entity)

    add_entities(entities, True)


class OutlookCalendarEventDevice(CalendarEventDevice):
    """A calendar event device."""

    def __init__(self, calendar_service, calendar, data, entity_id):
        """Create the Calendar event device."""
        self.data = OutlookCalendarData(
            calendar_service,
            calendar,
            data.get(CONF_FILTER),
            data.get(CONF_IGNORE_AVAILABILITY),
            data.get(CONF_MAX_RESULTS),
        )
        self._event = None
        self._name = data[CONF_NAME]
        self._offset = data.get(CONF_OFFSET, DEFAULT_CONF_OFFSET)
        self._offset_reached = False
        self.entity_id = entity_id

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return {"offset_reached": self._offset_reached}

    @property
    def event(self):
        """Return the next upcoming event."""
        return self._event

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    async def async_get_events(self, hass, start_date, end_date):
        """Get all events in a specific time frame."""
        return await self.data.async_get_events(hass, start_date, end_date)

    def update(self):
        """Update event data."""
        self.data.update()
        event = copy.deepcopy(self.data.event)
        if event is None:
            self._event = event
            return
        event = calculate_offset(event, self._offset)
        self._offset_reached = is_offset_reached(event)
        self._event = event


class OutlookCalendarData:
    """Class to utilize calendar service object to get next event."""

    def __init__(
        self, calendar_service, calendar_id, filter, ignore_availability, max_results
    ):
        """Set up how we are going to search the google calendar."""
        self.calendar_service = calendar_service
        self.calendar_id = calendar_id
        self.filter = filter
        self.ignore_availability = ignore_availability
        self.max_results = max_results
        self.event = None

    def _prepare_query(self):
        params = dict(DEFAULT_SEARCH_PARAMS)
        params["calendar_id"] = self.calendar_id
        if self.max_results:
            params["max_results"] = self.max_results
        if self.filter:
            params["filter"] = self.filter

        return params

    def _outlook_event_to_ha_event(self, event):
        data = {
            "description": event["subject"],
            "start": event["start"],
            "end": event["end"],
            "location": event["location"]["displayName"],
            "all_day": event["isAllDay"]
        }

        return data

    async def async_get_events(self, hass, start_date, end_date):
        """Get all events in a specific time frame."""
        params = await hass.async_add_executor_job(self._prepare_query)
        params["start_date"] = start_date.strftime('%Y-%m-%dT%H:%M:%S')
        params["end_date"] = end_date.strftime('%Y-%m-%dT%H:%M:%S')

        items = await hass.async_add_executor_job(self.calendar_service.get_events(**params))
        event_list = []
        for item in items:
            if not self.ignore_availability and "showAs" in item.keys():
                if item["showAs"] == "free":
                    event_list.append(self._outlook_event_to_ha_event(item))
            else:
                event_list.append(self._outlook_event_to_ha_event(item))
        return event_list

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data."""
        params = self._prepare_query()
        params["start_date"] = dt.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

        endDate = dt.now()
        endDate = endDate.replace(year = endDate.year + 1)
        params["end_date"] = endDate.strftime('%Y-%m-%dT%H:%M:%S')

        items = self.calendar_service.get_events(**params)

        new_event = None
        for item in items:
            if not self.ignore_availability and "showAs" in item.keys():
                if item["showAs"] == "free":
                    new_event = self._outlook_event_to_ha_event(item)
                    break
            else:
                new_event = self._outlook_event_to_ha_event(item)
                break

        self.event = new_event
