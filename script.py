import calendar
import datetime
import json
import os
import random
from typing import Tuple

import pdfplumber
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as api_build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_CALENDAR_COLORS = {
    1: {"name": "Lavender", "hex": "#7986cb"},
    2: {"name": "Sage", "hex": "#33b679"},
    3: {"name": "Grape", "hex": "#8e24aa"},
    4: {"name": "Flamingo", "hex": "#e67c73"},
    5: {"name": "Banana", "hex": "#f6c026"},
    6: {"name": "Tangerine", "hex": "#f5511d"},
    7: {"name": "Peacock", "hex": "#039be5"},
    8: {"name": "Graphite", "hex": "#616161"},
    9: {"name": "Blueberry", "hex": "#3f51b5"},
    10: {"name": "Basil", "hex": "#0b8043"},
    11: {"name": "Tomato", "hex": "#d60000"},
}
usable_colors = list(map(str, GOOGLE_CALENDAR_COLORS.keys()))
specified_colors = []

CALENDAR_ID = None
HOLIDAY_LIST_PATH = "BITS_Calendar_2024-25.pdf"


def auth():
    """
    Authorises the app to access the user's Google Calendar

    Args:
        None
    Returns:
        google.oauth2.credentials.Credentials: Google Calendar API credentials
    """
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


# region Google Calendar Helper Functions


def get_events(service, start_date, end_date):
    """
    Gets all events in the given date range

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
    Returns:
        list: List of events
    """
    events_result = (
        service.events()
        .list(
            calendarId=CALENDAR_ID,
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
    """
    Deletes all events in the given date range
    Can exclude events by name or colorId
    Can delete only events with a particular colorId
    Can force delete without confirmation

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
        excludeEvent (list): List of event names to exclude
        excludeColorId (list): List of colorIds to exclude
        onlyColorId (list): List of colorIds to include
        force (bool): Whether to force delete without confirmation
    Returns:
        None
    """
    # split date interval into months - [(start_date, end_date), ...)] - to avoid exceeding API quota
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    intervals = []
    while start_date <= end_date:
        if start_date.month == end_date.month:
            intervals.append(
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            )
            break
        month_end = datetime.datetime(
            start_date.year,
            start_date.month,
            calendar.monthrange(start_date.year, start_date.month)[1],
        )
        intervals.append(
            (start_date.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d"))
        )
        start_date = month_end + datetime.timedelta(days=1)

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
            service.events().delete(
                calendarId=CALENDAR_ID, eventId=event["id"]
            ).execute()
            print(f"Event deleted: {event['summary']}")


# endregion


# region Creating and Modifying Events


def add_classes(service, classes, start_date, end_date, custom: dict):
    """
    Adds all classes in the given date range

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        classes (list): List of classes
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
        custom (dict): Customisation dictionary
    Returns:
        None
    """
    start_date_original = start_date
    classes_colors = {}

    def get_color(i):
        """
        Gets the colorId for the event

        Args:
            i (dict): Class dictionary
        Returns:
            str: ColorId
        """
        if i["title"] in classes_colors:
            return classes_colors[i["title"]]
        if custom[i["title"]].get("color"):
            classes_colors[i["title"]] = custom[i["title"]]["color"]
            return custom[i["title"]]["color"]
        elif custom["course_grouping"]:
            # random unused color
            l = [
                x for x in usable_colors if str(x) not in list(classes_colors.values())
            ]
            if not l:
                l = [
                    x for x in classes_colors.values() if str(x) not in specified_colors
                ]
            x = str(random.choice(l))
            classes_colors[i["title"]] = x
            return x
        else:
            return custom["classes_color_ids"][i["type"]]

    for i in classes:
        # Finding the first date of the class
        start_date = datetime.datetime.strptime(start_date_original, "%Y-%m-%d")
        while start_date.strftime("%A").upper()[:2] not in i["days"]:
            start_date += datetime.timedelta(days=1)
        start_date = start_date.strftime("%Y-%m-%d")

        desc = (
            custom[i["title"]]["desc"]
            + ("<br>" if custom[i["title"]]["desc"] else "")
            + f"<ul><li><b>{i['type']} - {i['section']}</b></li><li><b>{i['name']}</b></li>"
            + (f"<li>{i['title']}</li>" if i["title"] != i["title"] else "")
            + "<br><u>Instructors</u>:<li>"
            + "</li><li>".join(i["instructors"])
            + "</li></ul>"
        )
        event = {
            "summary": custom[i["title"]]["title"]
            + ((" - " + i["type"][0]) if custom["course_grouping"] else ""),
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
                "overrides": [{"method": "popup", "minutes": custom["reminder"]}],
            },
            "colorId": get_color(i),
        }
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"Classes Added: {event['summary']}")


def del_classes_on_holidays(service, holidays):
    """
    Deletes all classes on holidays

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        holidays (list): List of holidays in the format YYYY-MM-DD
    Returns:
        None
    """
    print("\nDeleting classes on holidays...")
    for i in holidays:
        events = get_events(service, i, i)
        for event in events:
            try:
                if event["colorId"] not in usable_colors + specified_colors:
                    continue
            except KeyError:
                continue
            service.events().delete(
                calendarId=CALENDAR_ID, eventId=event["id"]
            ).execute()
            print(f"Event deleted: {event['summary']}")


def add_exams(
    service, exams, exams_start_end_dates: dict, custom: dict, timetable_ID, student_ID
):
    """
    Adds all exams and deletes classes during exams

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        exams (list): List of exams
        exams_start_end_dates (dict): Start and end dates of midsems and compres
        custom (dict): Customisation dictionary
        timetable_ID: Chrono timetable ID
        student_ID (str): Student ID
    Returns:
        None
    """
    exam_rooms = {}
    for i in custom["exam_rooms"]:
        exam_rooms[i] = get_room_numbers(
            custom["exam_rooms"][i],
            get_courses_enrolled(timetable_ID),
            student_ID,
        )
    for i in exams:
        exam = {
            "summary": i.split("|")[0],
            "start": {
                "dateTime": i.split("|")[2],
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": i.split("|")[3],
                "timeZone": "Asia/Kolkata",
            },
            "description": i.split("|")[1],
            "colorId": custom["exam_color_id"],
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": custom["reminder"]}],
            },
        }
        try:
            exam["location"] = exam_rooms[i.split("|")[1].lower()][i.split("|")[0]]
        except KeyError:
            pass
        service.events().insert(calendarId=CALENDAR_ID, body=exam).execute()
        print(f"{i.split('|')[1]} added: {i.split('|')[0]}")

    print("\nDeleting Classes during Exams...")
    del_events(
        service,
        exams_start_end_dates["midsem_start_date"],
        exams_start_end_dates["midsem_end_date"],
        excludeColorId=[custom["exam_color_id"]],
        onlyColorId=usable_colors + specified_colors,
        force=True,
    )
    del_events(
        service,
        exams_start_end_dates["compre_start_date"],
        exams_start_end_dates["compre_end_date"],
        excludeColorId=[custom["exam_color_id"]],
        onlyColorId=usable_colors + specified_colors,
        force=True,
    )


def add_exam_rooms(service, room_numbers, examtype):
    """
    Adds room numbers to the already created exam events

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        room_numbers (dict): Dictionary of course IDs and room numbers
        examtype (str): midsem or compre
    Returns:
        None
    """
    print("Adding Room Numbers to Exam Events...")
    print(room_numbers)
    exams_start_end_dates = get_exams_start_end_dates()
    events = get_events(
        service,
        exams_start_end_dates[f"{examtype}_start_date"],
        exams_start_end_dates[f"{examtype}_end_date"],
    )
    for event in events:
        if event["summary"] in room_numbers:
            event["location"] = room_numbers[event["summary"]]
            service.events().update(
                calendarId=CALENDAR_ID, eventId=event["id"], body=event
            ).execute()
            print(f"Room number added to {event['summary']}")
        else:
            print(f"Room number not found for {event['summary']}")


# endregion


# region Timetable Helper Functions


def get_exams_start_end_dates():
    """
    Gets the start and end dates of midsems and compres

    Args:
        None
    Returns:
        dict: Start and end dates of midsems and compres
    """
    courses_details = {}
    for i in json.loads(requests.get(f"https://chrono.crux-bphc.com/api/course").text):
        courses_details[i["id"]] = i

    return {
        "midsem_start_date": min(
            courses_details.values(),
            key=lambda x: (
                x["midsemStartTime"] if x["midsemStartTime"] else "9999-12-31T00:00:00Z"
            ),
        )["midsemStartTime"].split("T")[0],
        "midsem_end_date": max(
            courses_details.values(),
            key=lambda x: (
                x["midsemEndTime"] if x["midsemEndTime"] else "0000-01-01T00:00:00Z"
            ),
        )["midsemEndTime"].split("T")[0],
        "compre_start_date": min(
            courses_details.values(),
            key=lambda x: (
                x["compreStartTime"] if x["compreStartTime"] else "9999-12-31T00:00:00Z"
            ),
        )["compreStartTime"].split("T")[0],
        "compre_end_date": max(
            courses_details.values(),
            key=lambda x: (
                x["compreEndTime"] if x["compreEndTime"] else "0000-01-01T00:00:00Z"
            ),
        )["compreEndTime"].split("T")[0],
    }


def get_holidays(filepath):
    """
    Extracts list of holidays from the pdf

    Args:
        filepath (str): Path to the holiday calendar pdf file
    Returns:
        list: List of holidays in the format YYYY-MM-DD
    """
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


def get_courses_enrolled(timetable_ID):
    """
    Gets all courses enrolled in the given timetable

    Args:
        timetable_ID: Chrono timetable ID
    Returns:
        list: List of courses enrolled (course IDs)
    """
    print("Fetching courses enrolled...")
    timetable = json.loads(
        requests.get(f"https://chrono.crux-bphc.com/api/timetable/{timetable_ID}").text
    )

    try:
        if not timetable["sections"]:
            print("ID Error. Can't access timetable.")
            exit()
    except KeyError:
        print("ID Error. Can't access timetable.")
        exit()

    courses_enrolled = []
    for i in timetable["examTimes"]:
        courses_enrolled.append(i.split("|")[0])

    return courses_enrolled


def get_room_numbers(filepath, courses_enrolled, student_ID):
    """
    Extracts room numbers for enrolled courses from the pdf

    **Compatible with Compre 23-24 Sem 2**

    Args:
        filepath (str): Path to the seating arrangement pdf file
        courses_enrolled (list): List of courses enrolled (course IDs)
        student_ID (str): Student ID
    Returns:
        dict: Dictionary of course IDs and room numbers
    """
    print("Fetching exam room numbers...")
    pdf = pdfplumber.open(filepath)
    tables = []
    for i in pdf.pages:
        tables.extend(i.extract_tables())  # Extract all tables from the pdf

    room_numbers = {}

    # Parsing the tables of the pdf
    cur_course = ""
    for i in tables:
        for j in i:
            try:
                if any(
                    [
                        j[0].startswith(x)
                        for x in [
                            "BITS-PILANI",
                            "MID-SEMESTER",
                            "MIDSEMESTER",
                            "SEATING",
                            "COMPREHENSIVE",
                            "COURSE",
                            "Course",
                        ]
                    ]
                ):  # Skip headers
                    continue
                if j[0] in courses_enrolled:  # If course is enrolled
                    cur_course = j[0]
                elif j[0] != "":  # For courses with multiple rooms
                    cur_course = ""
                if cur_course:
                    ids = j[4].split("to")
                    if ids[0].strip() <= student_ID <= ids[1].strip():
                        room_numbers[cur_course] = j[3]
                        continue
            except:
                print(f"Error in PDF format for column:\n{j}")

    return room_numbers


# endregion


# region Util


def input_dates():
    """
    Gets the start and end dates from the user

    Args:
        None
    Returns:
        (str, str): (Start date, End date)
    """
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
    return start_date, end_date


def input_filepath():
    """
    Gets the filepath from the user

    Args:
        None
    Returns:
        str: Filepath
    """
    filepath = None
    while True:
        filepath = input("Enter filepath: ")
        if not filepath:
            print("Filepath cannot be empty")
            continue
        if not os.path.exists(filepath):
            print("File does not exist")
            continue
        break
    return filepath


# endregion


def initialise(service, timetable_ID, student_ID, start_date, end_date):
    """
    Makes lists of classes and exams and calls the respective functions

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        timetable_ID: Chrono timetable ID
        student_ID (str): Student ID
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
    Returns:
        dict: Customisation dictionary
    """
    # Found Chrono API endpoints by inspecting network traffic
    print("\nLoading Timetable...\n")
    timetable = json.loads(
        requests.get(f"https://chrono.crux-bphc.com/api/timetable/{timetable_ID}").text
    )

    try:
        if not timetable["sections"]:
            print("ID Error. Can't access timetable.")
            exit()
    except KeyError:
        print("ID Error. Can't access timetable.")
        exit()

    courses_details = {}
    for i in json.loads(requests.get(f"https://chrono.crux-bphc.com/api/course").text):
        courses_details[i["id"]] = i

    exams_start_end_dates = get_exams_start_end_dates()

    def convert_slots_to_days_hr(slot: Tuple[str, str]) -> Tuple[str, str]:
        """
        Converts chrono's time slot format to google calendar's format

        Args:
            slot (str, str): Chrono's time slot format (Day, Hour Number)
        Returns:
            (str, str): (Day, Hour) in google calendar's format
        """
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
        return (days[slot[0]], hours[slot[1]])

    types_dict = {"L": "Lecture", "T": "Tutorial", "P": "Practical"}
    classes = []
    for i in timetable["sections"]:
        timings = [
            convert_slots_to_days_hr((j.split(":")[2], j.split(":")[3]))
            for j in i["roomTime"]
        ]
        # Multiple hours for same course
        class_times = []
        for j in timings:
            block_period = [
                k
                for k in timings
                if (
                    k[0] == j[0]
                    and abs(int(k[1].split(":")[0]) - int(j[1].split(":")[0])) <= 2
                )
            ]
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
                    "end": (
                        k[0][1][:2] + ":50:00"
                        if days.count(days[0]) == 1
                        else str(int(k[0][1][:2]) + days.count(days[0]) - 1) + ":50:00"
                    ),
                    "section": i["type"] + str(i["number"]),
                    "instructors": i["instructors"],
                    "type": types_dict[i["type"]],
                    "name": courses_details[i["courseId"]]["name"].title(),
                }
            )

    for i in classes:
        if i["location"] == "WS":  # QOL
            i["location"] = "Workshop"
        elif i["location"] in [
            "A122",
            "A222",
            "B124",
        ]:  # Change Lab Courses to Practical
            i["type"] = "Practical"
            i["section"] = "P" + i["section"][1:]

    custom = customisation(classes)

    # Checking available colors that can be used
    for i in custom["remove_colors"]:
        usable_colors.remove(i)
    if custom.get("exam_color_id"):
        usable_colors.remove(custom.get("exam_color_id"))
        specified_colors.append(custom.get("exam_color_id"))
    if not custom["course_grouping"]:
        for i in custom["classes_color_ids"]:
            usable_colors.remove(custom["classes_color_ids"][i])
            specified_colors.append(custom["classes_color_ids"][i])
    for i in custom:
        if i not in [
            "reminder",
            "course_grouping",
            "exam_rooms",
            "classes_color_ids",
            "remove_colors",
            "exam_color_id",
        ]:
            if custom[i].get("color"):
                usable_colors.remove(custom[i]["color"])
                specified_colors.append(custom[i]["color"])

    add_classes(service, classes, start_date, end_date, custom)
    print("\nLoading Exam Schedule...")
    add_exams(
        service,
        timetable["examTimes"],
        exams_start_end_dates,
        custom,
        timetable_ID,
        student_ID,
    )
    return custom


def customisation(classes):
    """
    Lets the user customise the events created on google calendar

    Refer customisation_guidelines.md for more info

    Args:
        classes (list): List of classes (for course IDs)
    Returns:
        dict: Dictionary of customisation options
    """
    custom = {
        "reminder": 10,
        "course_grouping": 0,
        "exam_rooms": {},
        "classes_color_ids": {"Lecture": "10", "Tutorial": "9", "Practical": "11"},
        "remove_colors": [],
        "exam_color_id": "5",
    }

    for i in classes:
        custom[i["title"]] = {"title": i["title"], "desc": "", "color": ""}

    new_custom = {}
    print("\n*Please refer to customisation_guidelines.md before proceeding*\n")
    while True:
        print(
            """Customisation Menu:
1. Edit customisation.json (Requires knowledge of JSON)
2. Edit customisation interactively (Tedious but easy to use)
3. No customisation (Default)

"""
        )
        choice = input("Enter your choice: ")
        if choice == "1":
            with open("customisation.json", "w") as f:
                json.dump(custom, f, indent=4)
            print("Edit customisation.json and save the file")
            input("Press any key to continue...")
            with open("customisation.json", "r") as f:
                new_custom = json.load(f)

            # Add the default values for any missing keys and in nested keys
            for i in custom:
                if i not in new_custom:
                    new_custom[i] = custom[i]
                elif isinstance(custom[i], dict):
                    for j in custom[i]:
                        if j not in new_custom[i]:
                            new_custom[i][j] = custom[i][j]
            break
        elif choice == "2":
            while True:
                print(
                    """\nMenu:
1. Change reminder time
2. Group classes by course or type
3. Add Exam rooms if available
4. Change class type colors (Lecture, Tutorial, Practical)
5. Change exam color
6. Remove colors
7. Customise individual classes
8. Confirm and save customisation
"""
                )
                op = input("Enter your choice: ")
                if op == "1":
                    rem = input("Enter reminder time (in minutes): ")
                    try:
                        if not 0 <= int(rem) <= 40320:
                            raise ValueError
                        custom["reminder"] = int(rem)
                        print("Reminder time changed")
                    except ValueError:
                        print("Invalid Input\n")
                        continue
                elif op == "2":
                    print(
                        """\nMenu:
1. Group by type
2. Group by course
3. Back to Customisation Menu

"""
                    )
                    grp = input("Enter your choice: ")
                    if grp == "1":
                        custom["course_grouping"] = 0
                        print("Classes grouped by type")
                    elif grp == "2":
                        custom["course_grouping"] = 1
                        print("Classes grouped by course")
                    elif grp == "3":
                        continue
                    else:
                        print("Invalid Choice\n")
                        continue
                elif op == "3":
                    print(
                        """\nMenu:
1. Midsems
2. Compres
3. Back to Customisation Menu"""
                    )
                    exam = input("Enter your choice: ")
                    if exam == "1" or exam == "2":
                        fp = input_filepath()
                        custom["exam_rooms"]["midsem" if exam == "1" else "compre"] = fp
                        print("Seating Arrangement Added")
                    elif exam == "3":
                        continue
                    else:
                        print("Invalid Choice\n")
                        continue
                elif op == "4":
                    print(
                        """\nMenu:
1. Lecture
2. Tutorial
3. Practical
4. Back to Customisation Menu"""
                    )
                    color = input("Enter your choice: ")
                    id = input("Enter colorId: ")
                    try:
                        if not 1 <= int(id) <= 11:
                            raise ValueError
                        custom["classes_color_ids"][
                            (
                                "Lecture"
                                if color == "1"
                                else "Tutorial" if color == "2" else "Practical"
                            )
                        ] = id
                        print("Color changed")
                    except ValueError:
                        print("Invalid Input\n")
                        continue
                elif op == "5":
                    id = input("Enter colorId: ")
                    try:
                        if not 1 <= int(id) <= 11:
                            raise ValueError
                        custom["exam_color_id"] = id
                        print("Color changed")
                    except ValueError:
                        print("Invalid Input\n")
                        continue
                elif op == "6":
                    l = input("Enter colorIds to remove, separated by spaces: ").split()
                    try:
                        if not all(1 <= int(i) <= 11 for i in l):
                            raise ValueError
                        custom["remove_colors"].extend(l)
                        print("Colors removed")
                    except ValueError:
                        print("Invalid Input\n")
                        continue
                elif op == "7":
                    while True:
                        print("\nMenu:")
                        a = []
                        for i in range(len(classes)):
                            if classes[i]["title"] not in a:
                                a.append(classes[i]["title"])
                                print(f"{len(a)}. {classes[i]['title']}")
                        print(f"{len(a)+1}. Back to Customisation Menu\n")
                        course = input("Enter your choice: ")
                        if course == str(len(a) + 1):
                            break
                        try:
                            if not 1 <= int(course) <= len(a):
                                raise ValueError
                            while True:
                                print(
                                    f"""\nMenu {a[int(course)-1]}:
    1. Change title
    2. Add description
    3. Change color
    4. Back to Customisation Menu"""
                                )
                                edit = input("Enter your choice: ")
                                if edit == "1":
                                    title = input("Enter title: ")
                                    custom[a[int(course) - 1]]["title"] = title
                                    print("Title changed\n")
                                elif edit == "2":
                                    desc = input("Enter description: ")
                                    custom[a[int(course) - 1]]["desc"] = desc
                                    print("Description added\n")
                                elif edit == "3":
                                    id = input("Enter colorId: ")
                                    try:
                                        if not 1 <= int(id) <= 11:
                                            raise ValueError
                                        custom[a[int(course) - 1]]["color"] = id
                                        print("Color changed\n")
                                    except ValueError:
                                        print("Invalid Input\n")
                                        continue
                                elif edit == "4":
                                    break
                                else:
                                    print("Invalid Choice\n")
                                    continue
                        except ValueError:
                            print("Invalid Choice\n")
                            break
                elif op == "8":
                    break
                else:
                    print("Invalid Choice\n")
                    continue
            new_custom = custom
            break
        elif choice == "3":
            new_custom = custom
            break
        else:
            print("Invalid Choice\n")
            continue

    return new_custom


def main(creds):
    global CALENDAR_ID
    """
    Main function to run the script

    Args:
        creds (google.oauth2.credentials.Credentials): Google Calendar API credentials
    Returns:
        None
    """
    service = api_build("calendar", "v3", credentials=creds)

    existing_calendars = service.calendarList().list().execute()
    created_calendar = None

    for i in existing_calendars["items"]:
        if i["summary"] == "Timetable":
            created_calendar = i
            break
    else:
        created_calendar = (
            service.calendars()
            .insert(
                body={
                    "summary": "Timetable",
                    "timeZone": "Asia/Kolkata",
                }
            )
            .execute()
        )
    CALENDAR_ID = created_calendar["id"]
    print(f"Calendar ID: {CALENDAR_ID}")

    student_ID = None
    while True:
        student_ID = input("Enter your Student ID: ").strip().upper()
        if (
            len(student_ID) != 13
            or not student_ID[8:12].isdigit()
            or student_ID[-1] != "H"
        ):
            print("Incorrect Student ID")
            continue
        break

    timetable_ID = input("Enter timetable ID: ")

    while True:
        print(
            """\nMenu:
1. Add Classes and Exams
2. Update Exam Seating Arrangement
3. Delete Events in a Date Range
4. Exit
"""
        )
        choice = input("Enter your choice: ")
        if choice == "1":
            start_date, end_date = input_dates()
            custom = initialise(service, timetable_ID, student_ID, start_date, end_date)
            with open("customisation.json", "w") as f:
                json.dump(custom, f, indent=4)
            del_classes_on_holidays(service, get_holidays(HOLIDAY_LIST_PATH))
            print("\nDone.")
            break
        elif choice == "2":
            while True:
                print(
                    """\nMenu:
1. Midsems
2. Compres
3. Back to Main Menu"""
                )
                op = input("Enter your choice: ")
                if op == "1" or op == "2":
                    add_exam_rooms(
                        service,
                        get_room_numbers(
                            input_filepath(),
                            get_courses_enrolled(timetable_ID),
                            student_ID,
                        ),
                        "midsem" if op == "1" else "compre",
                    )
                elif op == "3":
                    break
                else:
                    print("Invalid Choice\n")
                    continue
        elif choice == "3":
            start_date, end_date = input_dates()
            print(
                "\nFilter events:\n- Leave blank to skip\n- Separate multiple entries with spaces\n\n"
            )
            excludeEvent = [i for i in input("Enter event names to exclude: ").split()]
            excludeColorId = [i for i in input("Enter colorIds to exclude: ").split()]
            onlyColorId = [
                i
                for i in input(
                    "Enter colorIds to include (If entered, only these events will be deleted): "
                ).split()
            ]
            del_events(
                service, start_date, end_date, excludeEvent, excludeColorId, onlyColorId
            )
        elif choice == "4":
            break
        else:
            print("Invalid Choice\n")
            continue


if __name__ == "__main__":
    creds = auth()
    main(creds=creds)
