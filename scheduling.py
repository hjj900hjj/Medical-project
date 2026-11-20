"""Local scheduling tools backed by a recurring duty roster and SQLite."""

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, time, timedelta


SLOT_LENGTH = timedelta(minutes=30)
SCHEDULE_DAYS = 21
PAGE_SIZE = 8


@dataclass(frozen=True)
class Slot:
    doctor_id: str
    start: datetime

    @property
    def timestamp(self):
        return self.start.isoformat(timespec='minutes')


class BookingAgent:
    def __init__(self, roster_path, database_path):
        self.database_path = database_path
        self.doctors = {}
        with open(roster_path, newline='', encoding='utf-8-sig') as roster:
            rows = csv.DictReader(roster)
            required = {'name', 'weekdays', 'start', 'end'}
            if not required.issubset(rows.fieldnames or []):
                raise ValueError('Roster requires name, weekdays, start and end columns.')
            for row in rows:
                self.add_shift(row)
        if not self.doctors:
            raise ValueError('The roster has no doctors.')
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY,
                    doctor_id TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    UNIQUE (doctor_id, starts_at)
                )
            ''')

    def add_shift(self, row):
        name = (row['name'] or '').strip()
        doctor_id = (row.get('id') or '').strip() or name
        department = (row.get('department') or '').strip()
        weekdays = {int(day) for day in (row['weekdays'] or '').split('|')}
        start, end = (time.fromisoformat(row[field] or '') for field in ('start', 'end'))
        if (not name or not weekdays <= set(range(1, 8)) or start >= end
                or any(value.tzinfo or value.second or value.microsecond
                       or value.minute % 30 for value in (start, end))):
            raise ValueError('Use a doctor name, weekdays 1–7 and same-day half-hour shift boundaries.')
        doctor = self.doctors.setdefault(doctor_id, (name, department, []))
        if doctor[:2] != (name, department):
            raise ValueError(f'Conflicting doctor details for {doctor_id}.')
        doctor[2].append((weekdays, start, end))

    def scheduled_slots(self, doctor_id, now):
        slots = set()
        for offset in range(SCHEDULE_DAYS):
            day = now.date() + timedelta(days=offset)
            for weekdays, start, end in self.doctors[doctor_id][2]:
                if day.isoweekday() not in weekdays:
                    continue
                cursor = datetime.combine(day, start)
                shift_end = datetime.combine(day, end)
                while cursor + SLOT_LENGTH <= shift_end:
                    if cursor > now:
                        slots.add(Slot(doctor_id, cursor))
                    cursor += SLOT_LENGTH
        return sorted(slots, key=lambda slot: slot.start)

    def available_slots(self, doctor_id, now):
        with closing(sqlite3.connect(self.database_path)) as connection:
            booked = {row[0] for row in connection.execute(
                'SELECT starts_at FROM appointments WHERE doctor_id = ?', (doctor_id,)
            )}
        return [slot for slot in self.scheduled_slots(doctor_id, now)
                if slot.timestamp not in booked]

    def book(self, slot, now):
        if slot not in self.scheduled_slots(slot.doctor_id, now):
            return None
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            cursor = connection.execute(
                'INSERT INTO appointments (doctor_id, starts_at) VALUES (?, ?) '
                'ON CONFLICT (doctor_id, starts_at) DO NOTHING',
                (slot.doctor_id, slot.timestamp),
            )
            return cursor.lastrowid if cursor.rowcount else None

    def run(self):
        doctor_ids = list(self.doctors)
        for number, doctor_id in enumerate(doctor_ids, 1):
            name, department, _ = self.doctors[doctor_id]
            label = f'{name} ({department})' if department else name
            print(f'{number}. {label}')
        choice = choose_number('Choose a doctor, or 0 to go back: ', len(doctor_ids))
        if choice == 0:
            return
        doctor_id = doctor_ids[choice - 1]
        slots = self.available_slots(doctor_id, datetime.now())
        if not slots:
            print('This doctor has no available times in the next 21 days.')
            return
        for offset in range(0, len(slots), PAGE_SIZE):
            page = slots[offset:offset + PAGE_SIZE]
            print('\nAvailable times (local time):')
            for number, slot in enumerate(page, 1):
                print(f'{number}. {slot.start:%a %Y-%m-%d %H:%M}')
            has_next = offset + len(page) < len(slots)
            next_option = len(page) + 1
            if has_next:
                print(f'{next_option}. More times')
            choice = choose_number('Choose a time, or 0 to go back: ', len(page) + has_next)
            if choice == 0:
                return
            if has_next and choice == next_option:
                continue
            slot = page[choice - 1]
            name = self.doctors[doctor_id][0]
            if input(f'Book {name} on {slot.start:%Y-%m-%d at %H:%M}? [y/N]: ').strip().lower() in ('y', 'yes'):
                booking_id = self.book(slot, datetime.now())
                if booking_id is None:
                    print('That time is no longer available. Type /book to see current times.')
                else:
                    print(f'Appointment booked. Confirmation #{booking_id}.')
            return


def choose_number(prompt, maximum):
    while True:
        try:
            number = int(input(prompt))
        except ValueError:
            number = -1
        if 0 <= number <= maximum:
            return number
        print('Enter one of the displayed numbers.')
