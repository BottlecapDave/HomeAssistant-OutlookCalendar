from .const import AUTHORITY_URL, REDIRECT_URL

import aiohttp

class MicrosoftAuthClient:

    def __init__(self, client_id, client_secret, scopes):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes

    def get_authorization_url(self, redirect_url):
        from urllib.parse import quote, urlencode

        authorize_url = '{0}{1}'.format(AUTHORITY_URL, '/common/oauth2/v2.0/authorize?{0}')

        params = { 'client_id': self.client_id,
            'redirect_uri': redirect_url,
            'response_type': 'code',
            'scope': ' '.join(str(i) for i in self.scopes)
        }

        signin_url = authorize_url.format(urlencode(params))

        return signin_url

    async def _fetch_access_token(self, session, url, data):
        async with session.post(url, data = data) as response:
            return await response.json()

    async def async_get_access_token(self, code):

        # Build the post form for the token request
        post_data = { 
            'grant_type': 'authorization_code',
            'code': code,
            'scope': ' '.join(str(i) for i in self.scopes),
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        async with aiohttp.ClientSession() as session:
            return await self._fetch_access_token(session, '{0}{1}'.format(AUTHORITY_URL, '/common/oauth2/v2.0/token'), post_data)


class OutlookCalendarService:

    def __init__(self, auth_client: MicrosoftAuthClient):
        self.auth_client = auth_client