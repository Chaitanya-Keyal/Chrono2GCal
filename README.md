# Google-Calendar-Timetable-Integration

##### Made for BPHC students to add their timetable to Google Calendar.

The timetable is extracted from [@crux-bphc](https://github.com/crux-bphc)'s [Chronofactorem](https://chrono.crux-bphc.com) and added to Google Calendar.

`credentials.json` is required to access the Google Calendar API. It can be downloaded from the [Google Calendar API Quickstart](https://developers.google.com/calendar/quickstart/python) page. The file should be placed in the same directory as `script.py`
### Features:
- Adds classes to Google Calendar with details like location, instructors, etc.
- Events are color coded based on the type of class.
- Event Titles can be customized.
- Adds exam events and deletes classes during the exam weeks.

- Can also delete multiple events at once, if required, with an option to exclude certain events.

### Todo:
- Add a json parser for customising event parameters like colors, titles, extra info in desc, etc.
- Delete classes on holidays
