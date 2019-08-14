"""Define constants for the Outlook Calendar component."""
from datetime import timedelta

DOMAIN = 'outlook_calendar'
CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'

AUTHORITY_URL = 'https://login.microsoftonline.com'
SCOPES = [ 'openid',
           'offline_access',
           'User.Read',
           'Calendars.Read' ]

AUTH_CALLBACK_PATH = '/api/outlook-calendar'
REDIRECT_URL = 'http://localhost:8123{0}'.format(AUTH_CALLBACK_PATH)

ENTITY_ID_FORMAT = DOMAIN + ".{}"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_TRACK_NEW = "track_new_calendar"

CONF_CAL_ID = "cal_id"
CONF_DEVICE_ID = "device_id"
CONF_NAME = "name"
CONF_ENTITIES = "entities"
CONF_TRACK = "track"
CONF_SEARCH = "search"
CONF_OFFSET = "offset"
CONF_IGNORE_AVAILABILITY = "ignore_availability"
CONF_MAX_RESULTS = "max_results"

DEFAULT_CONF_TRACK_NEW = True
DEFAULT_CONF_OFFSET = "!!"

EVENT_CALENDAR_ID = "calendar_id"
EVENT_DESCRIPTION = "description"
EVENT_END_CONF = "end"
EVENT_END_DATE = "end_date"
EVENT_END_DATETIME = "end_date_time"
EVENT_IN = "in"
EVENT_IN_DAYS = "days"
EVENT_IN_WEEKS = "weeks"
EVENT_START_CONF = "start"
EVENT_START_DATE = "start_date"
EVENT_START_DATETIME = "start_date_time"
EVENT_SUMMARY = "summary"
EVENT_TYPES_CONF = "event_types"

GROUP_NAME_ALL_CALENDARS = "Outlook Calendar Sensors"

SERVICE_SCAN_CALENDARS = "scan_for_calendars"
SERVICE_FOUND_CALENDARS = "found_calendar"
SERVICE_ADD_EVENT = "add_event"

DATA_INDEX = "outlook_calendars"

YAML_DEVICES = "outlook_calendars.yaml"

DATA_TOKEN = "token"
DATA_REFRESH_TOKEN = "refresh_token"
DATA_EXPIRES_IN = "expires_in"