"""Support for Outlook Calendar."""
import asyncio
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect, async_dispatcher_send)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util.dt import as_local, parse_datetime, utc_from_timestamp

from . import config_flow  # noqa  pylint_disable=unused-import
from .const import ( 
    DOMAIN,
    
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_TRACK_NEW,

    CONF_CAL_ID,
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_ENTITIES,
    CONF_TRACK,
    CONF_SEARCH,
    CONF_OFFSET,
    CONF_IGNORE_AVAILABILITY,
    CONF_MAX_RESULTS,

    DEFAULT_CONF_TRACK_N,EW,EVENT_CALENDAR_ID,
    EVENT_DESCRIPTION,
    EVENT_END_CO,NFEVENT_END_DATE,
    EVENT_END_DATETIME,e"
    EVENT_INEVENT_IN_DAYS,
    EVENT_IN_WEEKS,
    EVENT_START_CONF,
    EVENT_START_DATE,
    EVENT_START_DATETIME,
    EVENT_SUMMARY,
    EVENT_TYPES_CONF,

    GROUP_NAME_ALL_CALENDARS,

    SERVICE_SCAN_CALENDARS,
    SERVICE_FOUND_CALENDARS,
    SERVICE_ADD_EVENT,

    DATA_INDEX,

    YAML_DEVICES,

    SCOPES
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN:
        vol.Schema({
            vol.Required(CONF_CLIENT_ID): cv.string,
            vol.Required(CONF_CLIENT_SECRET): cv.string,
        })
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass, config):
    """Set up the Outlook Calendar component."""
    if DOMAIN not in config:
        return True

    if DATA_INDEX not in hass.data:
        hass.data[DATA_INDEX] = {}

    conf = config[DOMAIN]

    config_flow.register_flow_implementation(
        hass, 
        DOMAIN, 
        conf[CONF_CLIENT_ID],
        conf[CONF_CLIENT_SECRET])

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={'source': config_entries.SOURCE_IMPORT},
        ))

    return True

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Set up Outlook calendar from a config entry."""
    from pypoint import PointSession

    def token_saver(token):
        _LOGGER.debug("Saving updated token")
        entry.data[CONF_TOKEN] = token
        hass.config_entries.async_update_entry(entry, data={**entry.data})

    # Force token update.
    entry.data[CONF_TOKEN]["expires_in"] = -1
    session = PointSession(
        entry.data["refresh_args"]["client_id"],
        token=entry.data[CONF_TOKEN],
        auto_refresh_kwargs=entry.data["refresh_args"],
        token_saver=token_saver,
    )

    if not session.is_authorized:
        _LOGGER.error("Authentication Error")
        return False

    hass.data[DATA_CONFIG_ENTRY_LOCK] = asyncio.Lock()
    hass.data[CONFIG_ENTRY_IS_SETUP] = set()

    await async_setup_webhook(hass, entry, session)
    client = MinutPointClient(hass, entry, session)
    hass.data.setdefault(DOMAIN, {}).update({entry.entry_id: client})
    hass.async_create_task(client.update())

    return True

def setup_services(hass, hass_config, track_new_found_calendars, calendar_service):
    """Set up the service listeners."""

    def _found_calendar(call):
        """Check if we know about a calendar and generate PLATFORM_DISCOVER."""
        calendar = get_calendar_info(hass, call.data)
        if hass.data[DATA_INDEX].get(calendar[CONF_CAL_ID], None) is not None:
            return

        hass.data[DATA_INDEX].update({calendar[CONF_CAL_ID]: calendar})

        update_config(
            hass.config.path(YAML_DEVICES), hass.data[DATA_INDEX][calendar[CONF_CAL_ID]]
        )

        discovery.load_platform(
            hass,
            "calendar",
            DOMAIN,
            hass.data[DATA_INDEX][calendar[CONF_CAL_ID]],
            hass_config,
        )

    hass.services.register(DOMAIN, SERVICE_FOUND_CALENDARS, _found_calendar)

    def _scan_for_calendars(service):
        """Scan for new calendars."""
        service = calendar_service.get()
        cal_list = service.calendarList()
        calendars = cal_list.list().execute()["items"]
        for calendar in calendars:
            calendar["track"] = track_new_found_calendars
            hass.services.call(DOMAIN, SERVICE_FOUND_CALENDARS, calendar)

    hass.services.register(DOMAIN, SERVICE_SCAN_CALENDARS, _scan_for_calendars)


def do_setup(hass, hass_config, config):
    """Run the setup after we have everything configured."""
    # Load calendars the user has configured
    hass.data[DATA_INDEX] = load_config(hass.config.path(YAML_DEVICES))

    conf = config[DOMAIN]
    client_id = conf[CONF_CLIENT_ID]
    client_secret = conf[CONF_CLIENT_SECRET]
    
    auth = MicrosoftAuthClient(client_id, client_secret, SCOPES) 
    calendar_service = GoogleCalendarService(hass.config.path(TOKEN_FILE))
    track_new_found_calendars = convert(
        config.get(CONF_TRACK_NEW), bool, DEFAULT_CONF_TRACK_NEW
    )

    setup_services(hass, hass_config, track_new_found_calendars, calendar_service)

    for calendar in hass.data[DATA_INDEX].values():
        discovery.load_platform(hass, "calendar", DOMAIN, calendar, hass_config)

    # Look for any new calendars
    hass.services.call(DOMAIN, SERVICE_SCAN_CALENDARS, None)
    return True


class GoogleCalendarService:
    """Calendar service interface to Google."""

    def __init__(self, token_file):
        """Init the Google Calendar service."""
        self.token_file = token_file

    def get(self):
        """Get the calendar service from the storage file token."""
        import httplib2
        from oauth2client.file import Storage
        from googleapiclient import discovery as google_discovery

        credentials = Storage(self.token_file).get()
        http = credentials.authorize(httplib2.Http())
        service = google_discovery.build(
            "calendar", "v3", http=http, cache_discovery=False
        )
        return service


def get_calendar_info(hass, calendar):
    """Convert data from Google into DEVICE_SCHEMA."""
    calendar_info = DEVICE_SCHEMA(
        {
            CONF_CAL_ID: calendar["id"],
            CONF_ENTITIES: [
                {
                    CONF_TRACK: calendar["track"],
                    CONF_NAME: calendar["summary"],
                    CONF_DEVICE_ID: generate_entity_id(
                        "{}", calendar["summary"], hass=hass
                    ),
                }
            ],
        }
    )
    return calendar_info


def load_config(path):
    """Load the outlook_calendar_devices.yaml."""
    calendars = {}
    try:
        with open(path) as file:
            data = yaml.safe_load(file)
            for calendar in data:
                try:
                    calendars.update({calendar[CONF_CAL_ID]: DEVICE_SCHEMA(calendar)})
                except VoluptuousError as exception:
                    # keep going
                    _LOGGER.warning("Calendar Invalid Data: %s", exception)
    except FileNotFoundError:
        # When YAML file could not be loaded/did not contain a dict
        return {}

    return calendars


def update_config(path, calendar):
    """Write the outlook_calendar_devices.yaml."""
    with open(path, "a") as out:
        out.write("\n")
        yaml.dump([calendar], out, default_flow_style=False)