# Customisation Guidelines

`customisation.json` is used to customise the script's behaviour. It is a JSON file with the following fields:

- `reminder`:

  - Reminder time in minutes.
  - Default: `10`
  - Range: [0, 40320]

- `course_grouping`:

  - 0 => Group events by type
  - 1 => Group events by course
  - Default: `0`
    - If `course_grouping` is `0`:
      - All classes of the same type will be grouped together.
      - Color-coded with types mentioned in the description.
    - If `course_grouping` is `1`:
      - All classes of the same course will be grouped together.
      - Color-coded with types mentioned in the title and description

- `exam_rooms`:

  - Default: `{}`
  - Mapping of exam types to PDF paths if seating arrangements are available.
  - Example: `{"midsem": "midsem_pdf_path", "compre": "compre_pdf_path"}`

- `course IDs`:

  - Custom configurations for specific courses.
  - Default: `{"title": "Course ID", "desc": "", "color": ""}`
  - Example:
    - `<course ID>`: {
      - "title": "Custom title",
      - "desc": "Any extra description",
      - "color": "color_ID"
        }
    - If `color` is mentioned here, it overrides `course_grouping` color for that course.
    - If `color` is not mentioned here and `course_grouping` is `1`, color is assigned randomly from the list of available colors, and repeats colours if there are more courses than usable colors.

- `classes_color_ids`:

  - Default: `{"Lecture": "10", "Tutorial": "9", "Practical": "11"}`
  - Color mapping for event types.
  - If `course_grouping` is `0`, these color IDs are used.
  - If `course_grouping` is `1`, this is ignored, and color IDs are specified in `course IDs`.

- `remove_colors`:

  - Default: `[]`
  - List of color IDs not to be used for any event.
  - Use this to exclude colors used for other personal calendar events.

- `exam_color_id`:
  - Default: `"5"`
  - Color ID for exam events.

## Google Calendar Color IDs

| Color ID | Name      | Preview                                                    |
| -------- | --------- | ---------------------------------------------------------- |
| 1        | Lavender  | ![#7986cb](https://placehold.it/75x25/7986cb/000000?text=) |
| 2        | Sage      | ![#33b679](https://placehold.it/75x25/33b679/000000?text=) |
| 3        | Grape     | ![#8e24aa](https://placehold.it/75x25/8e24aa/000000?text=) |
| 4        | Flamingo  | ![#e67c73](https://placehold.it/75x25/e67c73/000000?text=) |
| 5        | Banana    | ![#f6c026](https://placehold.it/75x25/f6c026/000000?text=) |
| 6        | Tangerine | ![#f5511d](https://placehold.it/75x25/f5511d/000000?text=) |
| 7        | Peacock   | ![#039be5](https://placehold.it/75x25/039be5/000000?text=) |
| 8        | Graphite  | ![#616161](https://placehold.it/75x25/616161/000000?text=) |
| 9        | Blueberry | ![#3f51b5](https://placehold.it/75x25/3f51b5/000000?text=) |
| 10       | Basil     | ![#0b8043](https://placehold.it/75x25/0b8043/000000?text=) |
| 11       | Tomato    | ![#d60000](https://placehold.it/75x25/d60000/000000?text=) |

Sample `customisation.json`:

```json
{
  "reminder": 10,
  "course_grouping": 1,
  "MATH F111": {
    "title": "Maths",
    "desc": "Lite",
    "color": "6"
  },
  "CHEM F110": {
    "title": "Chem Lab",
    "desc": "Wear Shoes, Full Pants, and Lab Coat",
    "color": "7"
  },
  "exam_rooms": {
    "midsem": "Midsem_Seating_Sem1.pdf"
  },
  "remove_colors": ["2"],
  "exam_color_id": "8"
}
```
