DOMAIN = "outlook_calendar"
ENTITY_ID_FORMAT = DOMAIN + ".{}"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_TRACK_NEW = "track_new_calendar"

AUTH_CALLBACK_PATH = "/api/microsoft-outlook-calendar"
AUTHORIZATION_BASE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
SCOPES = ["Calendars.Read"]
AUTH_REQUEST_SCOPE = SCOPES + ["offline_access"]

CONF_CAL_ID = "cal_id"
CONF_DEVICE_ID = "device_id"
CONF_NAME = "name"
CONF_ENTITIES = "entities"
CONF_TRACK = "track"
CONF_FILTER = "filter"
CONF_OFFSET = "offset"
CONF_IGNORE_AVAILABILITY = "ignore_availability"
CONF_MAX_RESULTS = "max_results"

DEFAULT_CONF_TRACK_NEW = True
DEFAULT_CONF_OFFSET = "!!"

NOTIFICATION_ID = "google_calendar_notification"
NOTIFICATION_TITLE = "Google Calendar Setup"
GROUP_NAME_ALL_CALENDARS = "Google Calendar Sensors"

SERVICE_SCAN_CALENDARS = "scan_for_calendars"
SERVICE_FOUND_CALENDARS = "found_calendar"
SERVICE_ADD_EVENT = "add_event"

DATA_INDEX = "outlook_calendars"

YAML_DEVICES = f"outlook_calendars.yaml"
TOKEN_FILE = f".{DOMAIN}.token"