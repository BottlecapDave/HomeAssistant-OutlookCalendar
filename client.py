import re
import os

from requests.exceptions import HTTPError
from homeassistant.util.json import load_json, save_json
from requests_oauthlib import OAuth2Session
from aiohttp.web import Response
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from homeassistant.util import dt

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,

    SCOPES,

    TOKEN_FILE,
    AUTH_CALLBACK_PATH,
    TOKEN_URL
)

CONF_CAL_ID = "id"
CONF_CAL_NAME = "name"

def setup_outh_client(hass, config):
    config_path = hass.config.path(TOKEN_FILE)
    config_file = None
    if os.path.isfile(config_path):
        config_file = load_json(config_path)

    def token_saver(token):
        save_json(hass.config.path(TOKEN_FILE), token)

    # TODO: create a separate HTTP client class
    callback_url = f"{hass.config.api.base_url}{AUTH_CALLBACK_PATH}"
    oauth = OAuth2Session(
        config.get(CONF_CLIENT_ID),
        scope=SCOPES,
        redirect_uri=callback_url,
        token=config_file,
        auto_refresh_url=TOKEN_URL,
        auto_refresh_kwargs={
            'client_id': config.get(CONF_CLIENT_ID),
            'client_secret': config.get(CONF_CLIENT_SECRET),
        },
        token_updater=token_saver
    )
    retry = Retry(status=3, connect=3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    oauth.mount("http://", adapter)
    oauth.mount("https://", adapter)

    return oauth, config_file

class OutlookCalendarClient:

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

        api_endpoint = "https://graph.microsoft.com"
        self.calendars_endpoint = api_endpoint + "/v1.0/me/calendars"

    def get_calendars(self):
        try:
            self.logger.debug("Retrieve calendars")
            res = self.client.get(self.calendars_endpoint)
            res.raise_for_status()
            return res.json()['value']
        except HTTPError as e:
            self.logger.error("Unable to get calendars: %s. Response: %s", e, res.json())
            raise
        
    def get_events(self, calendar_id, max_results, start_date, end_date, filter=None):
        try:
            url = self.calendars_endpoint + f"/{calendar_id}/calendarView?$select=subject,start,end,showAs,location,isAllDay&top={max_results}&startDateTime={start_date}&endDateTime={end_date}&$orderBy=end/dateTime"
            if filter:
                url = url + f"&$filter={filter}"

            self.logger.info(f"Retrieve events: {url}")
            res = self.client.get(url)
            res.raise_for_status()
            return res.json()['value']
        except HTTPError as e:
            self.logger.error("Unable to get calendar events: %s. Response: %s", e, res.json())
            raise
    