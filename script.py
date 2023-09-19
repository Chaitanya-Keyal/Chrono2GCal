import calendar
import datetime
import json
import os

import pdfplumber
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as api_build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def auth():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # Refreshes the token if it is expired
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )  # Gets the user to login and authorise the app
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def get_holidays(filepath):
    pdf = pdfplumber.open(filepath)
    tables = []
    for i in pdf.pages:
        tables.extend(i.extract_tables())  # Extract all tables from the pdf
    holidays = []
    for i in tables:
        for j in i:
            if j[1] and j[1].endswith("(H)"):
                holidays.append(
                    datetime.datetime.strptime(j[0][: j[0].index("(")].strip(), "%B %d")
                )  # Extracts the date from the table
    for i in range(len(holidays)):
        holidays[i] = (
            holidays[i]
            .replace(
                year=datetime.datetime.today().year
                + (not (datetime.datetime.today().month <= holidays[i].month))
            )
            .strftime("%Y-%m-%d")
        )  # If the holiday is in the next year, add 1 to the year
    return sorted(holidays)


def delete_classes_on_holidays(service, holidays):
    print("Deleting classes on holidays...")
    for i in holidays:
        events = get_events(service, i, i)
        for event in events:
            try:
                if event["colorId"] not in ["9", "10", "11"]:
                    continue
            except KeyError:
                continue
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
            print(f"Event deleted: {event['summary']}")


def get_events(service, start_date, end_date):
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_date + "T00:00:00+05:30",
            timeMax=end_date + "T23:59:59+05:30",
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def del_events(
    service,
    start_date,
    end_date,
    excludeEvent=[],
    excludeColorId=[],
    onlyColorId=[],
    force=False,
):
    # split date interval into months - [(start_date, end_date), ...)]
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    intervals = []
    while start_date < end_date:
        if start_date.month == end_date.month:
            intervals.append(
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            )
            break
        intervals.append(
            (
                start_date.strftime("%Y-%m-%d"),
                datetime.datetime.strptime(
                    start_date.strftime("%Y-%m")
                    + "-"
                    + str(
                        calendar.monthrange(start_date.year, start_date.month)[1]
                    ).zfill(2)
                    + "T"
                    + "23:59:59",
                    "%Y-%m-%dT%H:%M:%S",
                ).strftime("%Y-%m-%d"),
            )
        )
        start_date = datetime.datetime.strptime(
            start_date.strftime("%Y-%m")
            + "-"
            + str(calendar.monthrange(start_date.year, start_date.month)[1]).zfill(2)
            + "T"
            + "23:59:59",
            "%Y-%m-%dT%H:%M:%S",
        )
        start_date += datetime.timedelta(days=1)

    # delete events in each interval
    for start_date, end_date in intervals:
        events = get_events(service, start_date, end_date)
        if not force:
            f = input(
                f"Are you sure you want to delete all events in the range {start_date} to {end_date}? (y/n): "
            )
            if f.lower() != "y":
                continue
        for event in events:
            try:
                if event["colorId"] in excludeColorId:
                    continue
                if onlyColorId and event["colorId"] not in onlyColorId:
                    continue
            except KeyError:
                continue
            if event["summary"] in excludeEvent:
                continue
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
            print(f"Event deleted: {event['summary']}")


def add_classes(service, classes, start_date, end_date):
    colors_dict = {
        "Tutorial": "9",
        "Lecture": "10",
        "Practical": "11",
    }
    start_date_original = start_date
    name_changed = {}  # For changing titles of classes
    for i in classes:
        original_name = i["title"]
        if original_name not in name_changed:
            f = input(
                f"\nAdding {i['title']}.\nDo you want to change the Event title? (y/n): "
            )
            while f.lower() == "y":
                i["title"] = input("Enter name: ")
                f = input(
                    f"\nChanged title to {i['title']}.\nDo you want to change it again? (y/n): "
                )
            name_changed[original_name] = i["title"]

        i["title"] = name_changed[original_name]

        # Finding the first date of the class
        start_date = datetime.datetime.strptime(start_date_original, "%Y-%m-%d")
        while start_date.strftime("%A").upper()[:2] not in i["days"]:
            start_date += datetime.timedelta(days=1)
        start_date = start_date.strftime("%Y-%m-%d")

        desc = (
            f"<ul><li><b>{i['type']} - {i['section']}</b></li><li><b>{i['name']}</b></li>"
            + (f"<li>{original_name}</li>" if original_name != i["title"] else "")
            + "<br><u>Instructors</u>:<li>"
            + "</li><li>".join(i["instructors"])
            + "</li></ul>"
        )

        event = {
            "summary": i["title"],
            "location": i["location"],
            "description": desc,
            "start": {
                "dateTime": f"{start_date}T{i['start']}+05:30",
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": f"{start_date}T{i['end']}+05:30",
                "timeZone": "Asia/Kolkata",
            },
            "recurrence": [
                f"RRULE:FREQ=WEEKLY;BYDAY={','.join(i['days'])};UNTIL={end_date.replace('-','')}T000000Z"
            ],
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
            "colorId": colors_dict[i["type"]],
        }
        service.events().insert(calendarId="primary", body=event).execute()
        print(f"Classes Added: {event['summary']}")


def add_exams(service, exams, exams_start_end_dates: dict):
    for i in exams:
        # Error in Chrono's Data
        if i.split("|")[0] == "CHEM F111":
            i = i.replace("CHEM", "EEE")
        elif i.split("|")[0] == "EEE F111":
            i = i.replace("EEE", "CHEM")

        exam = {
            "summary": i.split("|")[0],
            "start": {"dateTime": i.split("|")[2], "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": i.split("|")[3], "timeZone": "Asia/Kolkata"},
            "description": i.split("|")[1],
            "colorId": "5" if i.split("|")[1] == "MIDSEM" else "6",
        }
        service.events().insert(calendarId="primary", body=exam).execute()
        print(f"{i.split('|')[1]} added: {i.split('|')[0]}")

    print("Deleting Classes during Exams...")
    del_events(
        service,
        exams_start_end_dates["midsem_start_date"],
        exams_start_end_dates["midsem_end_date"],
        onlyColorId=["9", "10", "11"],
        force=True,
    )
    del_events(
        service,
        exams_start_end_dates["compre_start_date"],
        exams_start_end_dates["compre_end_date"],
        onlyColorId=["9", "10", "11"],
        force=True,
    )


def init_classes_exams(service, timetable_ID, start_date, end_date):
    # Found Chrono API endpoints by inspecting network traffic

    timetable = json.loads(
        requests.get(
            f"https://chrono.crux-bphc.com/backend/timetable/{timetable_ID}"
        ).text
    )

    try:
        if not timetable["sections"]:
            print("ID Error. Can't access timetable.")
            exit()
    except KeyError:
        print("ID Error. Can't access timetable.")
        exit()

    courses_details = {}
    for i in json.loads(
        requests.get(f"https://chrono.crux-bphc.com/backend/course").text
    ):
        courses_details[i["id"]] = i

    exams_start_end_dates = {
        "midsem_start_date": min(
            courses_details.values(),
            key=lambda x: x["midsemStartTime"]
            if x["midsemStartTime"]
            else "9999-12-31T00:00:00Z",
        )["midsemStartTime"].split("T")[0],
        "midsem_end_date": max(
            courses_details.values(),
            key=lambda x: x["midsemEndTime"]
            if x["midsemEndTime"]
            else "0000-01-01T00:00:00Z",
        )["midsemEndTime"].split("T")[0],
        "compre_start_date": min(
            courses_details.values(),
            key=lambda x: x["compreStartTime"]
            if x["compreStartTime"]
            else "9999-12-31T00:00:00Z",
        )["compreStartTime"].split("T")[0],
        "compre_end_date": max(
            courses_details.values(),
            key=lambda x: x["compreEndTime"]
            if x["compreEndTime"]
            else "0000-01-01T00:00:00Z",
        )["compreEndTime"].split("T")[0],
    }

    def convert_slots_to_days_hr(slot: str) -> (str, str):
        days = {
            "M": "MO",
            "T": "TU",
            "W": "WE",
            "Th": "TH",
            "F": "FR",
            "S": "SA",
            "Su": "SU",
        }
        hours = {
            "1": "08:00:00",
            "2": "09:00:00",
            "3": "10:00:00",
            "4": "11:00:00",
            "5": "12:00:00",
            "6": "13:00:00",
            "7": "14:00:00",
            "8": "15:00:00",
            "9": "16:00:00",
            "10": "17:00:00",
            "11": "18:00:00",
        }
        d, t = (
            slot.split(":") if ":" in slot else ("".join(slot[:-1]), "".join(slot[-1]))
        )
        return (days[d], hours[t])

    types_dict = {"L": "Lecture", "T": "Tutorial", "P": "Practical"}
    classes = []
    for i in timetable["sections"]:
        timings = [
            convert_slots_to_days_hr(j.split(":")[2] + j.split(":")[3])
            for j in i["roomTime"]
        ]
        class_times = []
        for j in timings:
            block_period = [k for k in timings if k[0] == j[0]]
            if len(block_period) > 1 and block_period not in class_times:
                class_times.append(block_period)
            diff_hrs = [k for k in timings if k[1] == j[1]]
            if diff_hrs not in class_times and len(block_period) == 1:
                class_times.append(diff_hrs)
        for k in class_times:
            days = [x[0] for x in k]
            classes.append(
                {
                    "title": i["roomTime"][0].split(":")[0],
                    "location": i["roomTime"][0].split(":")[1],
                    "days": list(set(days)),
                    "start": k[0][1],
                    "end": k[0][1][:2] + ":50:00"
                    if days.count(days[0]) == 1
                    else str(int(k[0][1][:2]) + days.count(days[0]) - 1) + ":50:00",
                    "section": i["type"] + str(i["number"]),
                    "instructors": i["instructors"],
                    "type": types_dict[i["type"]],
                    "name": courses_details[i["courseId"]]["name"].title(),
                }
            )

    for i in classes:
        if i["location"] == "WS":  # QOL
            i["location"] = "Workshop"
        elif i["location"] == "A222":  # Error in Chrono's Data
            i["type"] = "Practical"
            i["section"] = "P" + i["section"][1:]
        elif i["location"] == "B124":  # Error in Chrono's Data
            i["type"] = "Practical"
            i["section"] = "P" + i["section"][1:]

    add_classes(service, classes, start_date, end_date)
    add_exams(service, timetable["examTimes"], exams_start_end_dates)


def main(creds):
    service = api_build("calendar", "v3", credentials=creds)

    start_date = None
    while True:
        start_date = input(
            "Enter start date (YYYY-MM-DD) [Leave blank to start today]: "
        )
        if not start_date:
            start_date = datetime.datetime.today().strftime("%Y-%m-%d")
            break
        try:
            datetime.datetime.strptime(start_date, "%Y-%m-%d")
            break
        except ValueError:
            print("\nIncorrect date format, should be YYYY-MM-DD")
            continue

    end_date = None
    while True:
        end_date = input("Enter semester end date (Excluded) (YYYY-MM-DD): ")
        try:
            datetime.datetime.strptime(end_date, "%Y-%m-%d")
            break
        except ValueError:
            print("\nIncorrect date format, should be YYYY-MM-DD")
            continue

    timetable_ID = int(input("Enter timetable ID: "))

    init_classes_exams(service, timetable_ID, start_date, end_date)
    delete_classes_on_holidays(service, get_holidays("BPHC_Calendar_23_24.pdf"))

    # del_events(
    #     service,
    #     start_date,
    #     end_date,
    #     onlyColorId=["5", "6", "9", "10", "11"],
    #     force=True,
    # )


if __name__ == "__main__":
    creds = auth()
    main(creds=creds)
