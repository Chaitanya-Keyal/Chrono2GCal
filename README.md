# Chrono2GCal

<b>Made for BPHC students to add their timetable to Google Calendar directly from [Chronofactorem](https://chrono.crux-bphc.com) developed by [@crux-bphc](https://github.com/crux-bphc).</b>

### Features:

- Adds classes to Google Calendar with details like location, instructors, etc.
- Events are customizable.
  - Colors
  - Reminders
  - Titles
  - Descriptions
- Exams are also added, along with the allotted room for each student.
- Deletes classes on holidays and exam days.
- Can delete events in bulk with filters.

### Usage:

- `credentials.json` is required to access the Google Calendar API. It can be downloaded from the [Google Calendar API Quickstart](https://developers.google.com/calendar/quickstart/python) page. The file should be placed in the same directory as `script.py`
- A valid `chronofactoreom` timetable ID is required (Obviously, make your timetable first). It is the last four characters of the URL of the timetable. For example, if the URL is `https://chrono.crux-bphc.com/tt/xUrC`, the timetable ID is `xUrC`.
- `cd` into the directory containing `script.py`
- Install the required packages using `pip install -r requirements.txt`
- Run `script.py`. It will prompt you to authorize the script to access your Google Calendar.
- Follow further instructions in the terminal.

### Notes:

- For exams seating arrangement, the PDFs in `pdfs/` are supported. If other PDFs follow the same format, that will also work. If not, I will be adding support for each new PDF as they are released by TTD.
- Customisations are parsed from a JSON file, simplifying possible future GUI development.
