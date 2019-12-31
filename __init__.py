"""Support for Google - Calendar Event Devices."""
from datetime import datetime, timedelta
import logging
import os

from googleapiclient import discovery as google_discovery
from aiohttp.web import Response
import httplib2
from oauth2client.client import (
    FlowExchangeError,
    OAuth2DeviceCodeError,
    OAuth2WebServerFlow,
)
from oauth2client.file import Storage
import voluptuous as vol
from voluptuous.error import Error as VoluptuousError
import yaml

from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.event import track_time_change
from homeassistant.util import convert, dt
from homeassistant.util.json import save_json
from homeassistant.core import callback
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    ENTITY_ID_FORMAT,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_TRACK_NEW,
    CONF_CAL_ID,
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_ENTITIES,
    CONF_TRACK,
    CONF_FILTER,
    CONF_OFFSET,
    CONF_IGNORE_AVAILABILITY,
    CONF_MAX_RESULTS,
    DEFAULT_CONF_TRACK_NEW,
    DEFAULT_CONF_OFFSET,
    NOTIFICATION_ID,
    NOTIFICATION_TITLE,
    GROUP_NAME_ALL_CALENDARS,
    SERVICE_SCAN_CALENDARS,
    SERVICE_FOUND_CALENDARS,
    SERVICE_ADD_EVENT,
    DATA_INDEX,
    YAML_DEVICES,
    TOKEN_FILE,

    AUTH_CALLBACK_PATH,
    AUTH_REQUEST_SCOPE,
    SCOPES,
    AUTHORIZATION_BASE_URL,
    TOKEN_URL
)

from .client import ( 
    setup_outh_client, 
    OutlookCalendarClient
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
                vol.Optional(CONF_TRACK_NEW): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_SINGLE_CALSEARCH_CONFIG = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_IGNORE_AVAILABILITY, default=True): cv.boolean,
        vol.Optional(CONF_OFFSET): cv.string,
        vol.Optional(CONF_FILTER): cv.string,
        vol.Optional(CONF_TRACK): cv.boolean,
        vol.Optional(CONF_MAX_RESULTS): cv.positive_int,
    }
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CAL_ID): cv.string,
        vol.Required(CONF_ENTITIES, None): vol.All(
            cv.ensure_list, [_SINGLE_CALSEARCH_CONFIG]
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

def request_configuration(hass, config, authorization_url):
    configurator = hass.components.configurator
    hass.data[DOMAIN] = configurator.request_config(
        "Outlook Calendar",
        lambda _: None,
        link_name="Link Outlook Calendar account",
        link_url=authorization_url,
        description="To link your Outlook Calendar account, "
                    "click the link, login, and authorize:",
        submit_caption="I authorized successfully",
    )

def do_authentication(hass, hass_config, config):
    
    _LOGGER.info("Do authentication")

    oauth, config_file = setup_outh_client(hass, config)

    if not config_file:
        _LOGGER.info(f"Redirect URI: {oauth.redirect_uri}")
        # NOTE: request extra scope for the offline access and avoid
        # exception related to differences between requested and granted scopes
        oauth.scope = AUTH_REQUEST_SCOPE
        authorization_url, state = oauth.authorization_url(AUTHORIZATION_BASE_URL)
        oauth.scope = SCOPES
        request_configuration(hass, config, authorization_url)

    hass.http.register_view(
        OutlookCalendarAuthCallbackView(oauth, config.get(CONF_CLIENT_SECRET), [hass, hass_config, config])
    )

    return True

class OutlookCalendarAuthCallbackView(HomeAssistantView):

    url = AUTH_CALLBACK_PATH
    name = "auth:outlook_calendar:callback"
    requires_auth = False

    def __init__(self, oauth, client_secret, setup_args):
        self.oauth = oauth
        self.client_secret = client_secret
        self.setup_args = setup_args

    @callback
    def get(self, request):
        hass = request.app["hass"]
        data = request.query

        html_response = """<html><head><title>Microsoft Outlook Calendar authorization</title></head>
                           <body><h1>{}</h1></body></html>"""

        if data.get("code") is None:
            error_msg = "No code returned from Microsoft Graph Auth API"
            _LOGGER.error(error_msg)
            return Response(text=html_response.format(error_msg), content_type="text/html")

        token = self.oauth.fetch_token(TOKEN_URL, client_secret=self.client_secret, code=data.get("code"))

        save_json(hass.config.path(TOKEN_FILE), token)

        response_message = """Outlook Calendar has been successfully authorized!
                              You can close this window now!"""

        hass.async_add_job(do_setup, *self.setup_args)

        return Response(
            text=html_response.format(response_message), content_type="text/html"
        )

def setup(hass, config):
    """Set up the Google platform."""
    if DATA_INDEX not in hass.data:
        hass.data[DATA_INDEX] = {}

    conf = config.get(DOMAIN, {})
    if not conf:
        # component is set up by tts platform
        return True

    token_file = hass.config.path(TOKEN_FILE)
    if not os.path.isfile(token_file):
        do_authentication(hass, config, conf)
    else:
        do_setup(hass, config, conf)

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
        _LOGGER.info("Scan for calendars")
        calendars = calendar_service.get_calendars()
        for calendar in calendars:
            calendar["track"] = track_new_found_calendars
            hass.services.call(DOMAIN, SERVICE_FOUND_CALENDARS, calendar)

    hass.services.register(DOMAIN, SERVICE_SCAN_CALENDARS, _scan_for_calendars)

    return True


def do_setup(hass, hass_config, config):
    """Run the setup after we have everything configured."""

    _LOGGER.info("Do setup")

    # Load calendars the user has configured
    hass.data[DATA_INDEX] = load_config(hass.config.path(YAML_DEVICES))

    oauth, config_file = setup_outh_client(hass, config)

    calendar_service = OutlookCalendarClient(client=oauth, logger=_LOGGER)
    track_new_found_calendars = convert(
        config.get(CONF_TRACK_NEW), bool, DEFAULT_CONF_TRACK_NEW
    )
    setup_services(hass, hass_config, track_new_found_calendars, calendar_service)

    for calendar in hass.data[DATA_INDEX].values():
        discovery.load_platform(hass, "calendar", DOMAIN, calendar, hass_config)

    # Look for any new calendars
    hass.services.call(DOMAIN, SERVICE_SCAN_CALENDARS, None)
    return True

def get_calendar_info(hass, calendar):
    """Convert data from Google into DEVICE_SCHEMA."""
    calendar_info = DEVICE_SCHEMA(
        {
            CONF_CAL_ID: calendar["id"],
            CONF_ENTITIES: [
                {
                    CONF_TRACK: calendar["track"],
                    CONF_NAME: calendar["name"],
                    CONF_DEVICE_ID: generate_entity_id(
                        "{}", calendar["name"], hass=hass
                    ),
                }
            ],
        }
    )
    return calendar_info


def load_config(path):
    """Load the google_calendar_devices.yaml."""
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
    """Write the google_calendar_devices.yaml."""
    with open(path, "a") as out:
        out.write("\n")
        yaml.dump([calendar], out, default_flow_style=False)
