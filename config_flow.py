"""Config flow for Outlook Calendar."""
import asyncio
from collections import OrderedDict
import logging

from urllib.parse import quote, urlencode

import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback

from .const import AUTHORITY_URL, CLIENT_ID, CLIENT_SECRET, DOMAIN, SCOPES

AUTH_CALLBACK_PATH = '/api/outlook-calendar'
AUTH_CALLBACK_NAME = 'api:outlook-calendar'

DATA_FLOW_IMPL = 'outlook_calendar_flow_implementation'

_LOGGER = logging.getLogger(__name__)


@callback
def register_flow_implementation(hass, domain, client_id, client_secret):
    """Register a flow implementation.

    domain: Domain of the component responsible for the implementation.
    name: Name of the component.
    client_id: Client id.
    client_secret: Client secret.
    """
    if DATA_FLOW_IMPL not in hass.data:
        hass.data[DATA_FLOW_IMPL] = OrderedDict()

    hass.data[DATA_FLOW_IMPL][domain] = {
        CLIENT_ID: client_id,
        CLIENT_SECRET: client_secret,
    }


@config_entries.HANDLERS.register('outlook_calendar')
class OutlookCalendarFlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize flow."""
        self.flow_impl = None

    async def async_step_import(self, user_input=None):
        """Handle external yaml configuration."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason='already_setup')

        self.flow_impl = DOMAIN

        return await self.async_step_auth()

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        flows = self.hass.data.get(DATA_FLOW_IMPL, {})

        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason='already_setup')

        if not flows:
            _LOGGER.debug("no flows")
            return self.async_abort(reason='no_flows')

        if len(flows) == 1:
            self.flow_impl = list(flows)[0]
            return await self.async_step_auth()

        if user_input is not None:
            self.flow_impl = user_input['flow_impl']
            return await self.async_step_auth()

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required('flow_impl'):
                vol.In(list(flows))
            }))

    async def async_step_auth(self, user_input=None):
        """Create an entry for auth."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason='external_setup')

        errors = {}

        if user_input is not None:
            errors['base'] = 'follow_link'

        try:
            with async_timeout.timeout(10):
                url = await self._get_authorization_url()
        except asyncio.TimeoutError:
            return self.async_abort(reason='authorize_url_timeout')
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error generating auth url")
            return self.async_abort(reason='authorize_url_fail')

        return self.async_show_form(
            step_id='auth',
            description_placeholders={'authorization_url': url},
            errors=errors,
        )

    async def _get_authorization_url(self):
        """Create Outlook Calendar session and get authorization url."""
        flow = self.hass.data[DATA_FLOW_IMPL][self.flow_impl]
        client_id = flow[CLIENT_ID]
        client_secret = flow[CLIENT_SECRET]
        authorize_url = '{0}{1}'.format(AUTHORITY_URL, '/common/oauth2/v2.0/authorize?{0}')

        params = { 'client_id': client_id,
            'redirect_uri': 'http://localhost:8123/{0]'.format(AUTH_CALLBACK_PATH),
            'response_type': 'code',
            'scope': ' '.join(str(i) for i in SCOPES)
        }

        signin_url = authorize_url.format(urlencode(params))

        self.hass.http.register_view(OutlookCalendarAuthCallbackView())

        return signin_url

    async def async_step_code(self, code=None):
        """Received code for authentication."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason='already_setup')

        if code is None:
            return self.async_abort(reason='no_code')

        _LOGGER.debug("Should close all flows below %s",
                      self.hass.config_entries.flow.async_progress())
        # Remove notification if no other discovery config entries in progress

        return await self._async_create_session(code)

    async def _async_create_session(self, code):
        """Create Outlook Calendar session and entries."""
        flow = self.hass.data[DATA_FLOW_IMPL][DOMAIN]
        client_id = flow[CLIENT_ID]
        client_secret = flow[CLIENT_SECRET]
        point_session = PointSession(
            client_id,
            client_secret=client_secret,
        )

        token = await self.hass.async_add_executor_job(
            point_session.get_access_token, code)
            
        _LOGGER.debug("Got new token")

        if not point_session.is_authorized:
            _LOGGER.error('Authentication Error')
            return self.async_abort(reason='auth_error')

        _LOGGER.info('Successfully authenticated Point')
        user_email = point_session.user().get('email') or ""

        return self.async_create_entry(
            title=user_email,
            data={
                'token': token,
                'refresh_args': {
                    'client_id': client_id,
                    'client_secret': client_secret
                }
            },
        )


class OutlookCalendarAuthCallbackView(HomeAssistantView):
    """Minut Authorization Callback View."""

    requires_auth = False
    url = AUTH_CALLBACK_PATH
    name = AUTH_CALLBACK_NAME

    @staticmethod
    async def get(request):
        """Receive authorization code."""
        hass = request.app['hass']
        if 'code' in request.query:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={'source': 'code'},
                    data=request.query['code'],
                ))
        return "OK!"
