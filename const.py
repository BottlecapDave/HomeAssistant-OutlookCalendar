"""Define constants for the Outlook Calendar component."""
from datetime import timedelta

DOMAIN = 'outlook_calendar'
CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'

SCAN_INTERVAL = timedelta(minutes=1)

CONF_WEBHOOK_URL = 'webhook_url'
AUTHORITY_URL = 'https://login.microsoftonline.com'
SCOPES = [ 'openid',
           'User.Read',
           'Mail.Read' ]