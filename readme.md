# Home Assistant - Outlook Calendar Component

This custom component for Home Assistant provides read only sensors representing events within Microsoft Outlook Calendars.

The code is based on the [Google Calendar](https://www.home-assistant.io/integrations/calendar.google/) integration along with [Microsoft To Do](https://github.com/black-roland/homeassistant-microsoft-todo) for authenticating.

This is currently a `work in progress`, and will possibly change to provide a better user experience or new functionality.

## Installation

### Prerequisites

In order to use this component, you'll need to create an app that the component can authenticate on behalf of. This can be done by following the instructions below, which were adapted from [Microsoft docs](https://docs.microsoft.com/en-us/outlook/rest/python-tutorial#register-the-app).

1. Open a browser and navigate to the Azure Active Directory admin center. Login using a personal account (aka: Microsoft Account) or Work or School Account.

2. Select Azure Active Directory in the left-hand navigation, then select App registrations under Manage.

3. Select New registration. On the Register an application page, set the values as follows.

    a. Set Name to `Home Assistant`

    b. Set Supported account types to `Accounts in any organizational directory and personal Microsoft accounts`.
    
    c. Under `Redirect URI`, set the first drop-down to `Web` and set the value to match your Home Assistant [base url](https://www.home-assistant.io/integrations/http/) with the addition of `/api/microsoft-outlook-calendar`. For example `https://hassio.local:8123/api/microsoft-outlook-calendar`.

    If your instance of home assistant isn't accessible in the web, then set this to `localhost` (e.g. `http://localhost:8123/api/microsoft-outlook-calendar`)

4. Choose `Register`. On the `Home Assistant` page, copy the value of the `Application (client) ID` and save it in your `secrets.yaml` with the key `outlook_client_id`.

5. Select `Authentication` under `Manage`. Locate the `Implicit grant` section and enable `ID tokens`. Choose `Save`.

6. Select `Certificates & secrets` under `Manage`. Select the `New client secret` button. Enter a value in `Description` and select `Never` as the option for `Expires` and choose `Add`.

7. Copy the `client secret` value before you leave this page. Save it in your `secrets.yaml` with the key `outlook_client_secret`.

### Custom Component

Add the contents of the [src](./src) folder with the name `outlook_calendar` into your [config directory](https://developers.home-assistant.io/docs/en/creating_component_loading.html).

### Configuration.yaml

Add the following to your `configuration.yaml`.

```yaml
outlook_calendar:
  client_id: !secret outlook_client_id
  client_secret: !secret outlook_client_secret
  track_new_calendar: false # This is optional, and is true by default.
```

Restart `Home Assistant`, and once it comes online you should have a notification prompting you to authorise your account with the component.

If the redirect url you specified isn't public facing, there's a chance that you'll get a `page not found` error. Just update `localhost` to your `Home Assistant` instance (e.g. `http://hassio.local:8123/api/microsoft-outlook-calendar`) and refresh your browser. You should now be greeted with a page stating that the authentication was successful and a file `.outlook_calendar.token` should now be present in the root of your `Home Assistant` configuration directory.

## Calendar Configuration

// TODO