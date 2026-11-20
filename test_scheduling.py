import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from scheduling import BookingAgent


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.roster = Path(folder.name) / 'roster.csv'
        self.database = Path(folder.name) / 'appointments.sqlite3'
        self.roster.write_text('id,name,weekdays,start,end\nd1,Dr. Test,1,09:00,11:00\n',
                               encoding='utf-8')
        self.agent = BookingAgent(self.roster, self.database)
        self.now = datetime(2026, 11, 16, 9, 15)

    def test_three_week_window_excludes_elapsed_and_out_of_window_slots(self):
        slots = self.agent.available_slots('d1', self.now)
        self.assertEqual(len(slots), 11)
        self.assertEqual(slots[0].start, datetime(2026, 11, 16, 9, 30))
        self.assertEqual(slots[-1].start, datetime(2026, 11, 30, 10, 30))
        self.assertIsNone(self.agent.book(slots[0], slots[0].start))

    def test_competing_bookings_only_create_one_persistent_appointment(self):
        other_agent = BookingAgent(self.roster, self.database)
        slot = self.agent.available_slots('d1', self.now)[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda agent: agent.book(slot, self.now),
                                    (self.agent, other_agent)))
        self.assertCountEqual(results, [1, None])
        reopened_agent = BookingAgent(self.roster, self.database)
        self.assertNotIn(slot, reopened_agent.available_slots('d1', self.now))
