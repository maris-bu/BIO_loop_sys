import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app_server import Engine


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.engine = Engine(Path(self.temp.name), start_simulator=False)

    def tearDown(self):
        self.temp.cleanup()

    def test_checkin_changes_recommendation(self):
        result = self.engine.checkin("drained")
        self.assertEqual(result["protocol"]["title"], "The 6-minute downshift")
        self.assertGreaterEqual(result["capacity"], 5)
        self.assertLessEqual(result["capacity"], 98)

    def test_session_has_personal_baseline(self):
        session = self.engine.begin(360, "steady")
        self.assertTrue(session["session_id"])
        self.assertGreater(session["baseline_rmssd"], 0)
        self.assertEqual(session["duration"], 360)

    def test_rejects_unknown_mood(self):
        with self.assertRaises(ValueError):
            self.engine.checkin("mystery")

    def test_dashboard_explains_learning(self):
        session = self.engine.begin(360, "steady", "Test User", "Polar H10")
        self.engine.complete(session["session_id"])
        dashboard = self.engine.dashboard()
        self.assertEqual(len(dashboard["week"]), 7)
        self.assertEqual(dashboard["learning"]["sessions_observed"], 0)
        dashboard = self.engine.dashboard("Test User")
        self.assertGreater(dashboard["learning"]["sessions_observed"], 0)
        self.assertTrue(dashboard["sessions"])


if __name__ == "__main__":
    unittest.main()
