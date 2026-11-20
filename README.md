# Medical-project
CSCI 4150 project

Run `python cli.py` after creating `config.json` from `config.example.json`.

The terminal offers booking after a preliminary assessment. Type `yes` to
choose a doctor and time, or use `/book` to open scheduling directly. The
terminal asks for confirmation before creating the appointment.

The default roster is `data/doctors.csv`. To use another roster, run
`python cli.py --doctors path/to/roster.csv`. A minimal CSV looks like this:

```csv
id,name,weekdays,start,end
d1,Dr. Ethan Lin,1|3|5,09:00,12:00
```

Weekdays run from 1 (Monday) to 7 (Sunday). Each row defines a recurring,
same-day shift with half-hour boundaries. Use the same stable doctor ID on
multiple rows for that doctor's shifts. If `id` is omitted, the doctor name
serves as the ID. An optional `department` column is displayed during selection.

Scheduling shows future 30-minute slots from today through 20 days from
today, using the computer's local time. Reservations persist in
`appointments.sqlite3` and are shared by CLI sessions using that database.
The database stores the doctor ID, start time and confirmation number.
