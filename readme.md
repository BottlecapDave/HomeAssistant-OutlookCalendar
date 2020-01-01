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

When you first authenticate with the component, or call the `outlook_calendar.scan_for_calendars` service, a file called `outlook_calendars.yaml` will be generated in the root of your `Home Assistant` configuration directory.

This will look something like.

```yaml
- cal_id: ***
  entities:
  - device_id: main
    ignore_availability: true
    name: Main
    track: true
- cal_id: ***
  entities:
  - device_id: family_calendar
    ignore_availability: true
    name: Family Calendar
    track: false
  - device_id: guests
    ignore_availability: true
    name: Guests
    track: true
    filter: contains(subject,'visit') or contains(subject,'staying')
```

### Configuration Variables

**cal_id** - string/required

The unique id for this calendar. This is generated by Outlook and must not be changed.

#### entities - list/required

**device_id** - string/required

The name that all your automations/scripts will use to reference this device.

**name** - string/required

What is the name of your sensor that you’ll see in the frontend.

**track** - boolean/required

Should we create a sensor (true) or ignore it (false). 

The default value is true.

**filter** - string/optional

The criteria that must be present for events to match. This supports anything that is supported by the [$filter](https://docs.microsoft.com/en-gb/graph/query-parameters#filter-parameter) query parameter.

**offset** - string/optional

A set of characters that precede a number in the event title for designating a pre-trigger state change on the sensor. This should be in the format of HH:MM or MM.

The default value is `!!`

**ignore_availability** - boolean/optional

If set to true, we'll ignore availability for the event. Otherwise we'll only include events that are marked as free.

The default value is `true`.

**max_results** - integer/optional

The maximum number of entries to retrieve at any given time. The default value is 5.

---

From the example above, we would end up with the binary sensors `calendar.main` and `calendar.guests` which will toggle themselves on/off based on events on the same calendar that match the filter value set for each. As we don't have any filtering set for `calendar.main`, it will not filter events out and always show the next event available.

### Sensor Attributes


* **offset_reached**: If set in the event title and parsed out will be on/off once the offset in the title in minutes is reached. So the title Very important meeting #Important !!-10 would trigger this attribute to be on 10 minutes before the event starts.
* **all_day**: true/false if this is an all day event. Will be false if there is no event found.
* **message**: The event title.
* **description**: Not set.
* **location**: The event Location.
* **start_time**: Start time of event.
* **end_time**: End time of event.
