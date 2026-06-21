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
        self.assertEqual(dashboard["today"]["readiness"], "Connect device")
        self.assertEqual(dashboard["goal"]["target"], 3)

    def test_checkin_is_saved_for_recommendations(self):
        self.engine.checkin("drained", "Test User")
        dashboard = self.engine.dashboard("Test User")
        self.assertEqual(dashboard["today"]["mood"], "drained")
        self.assertEqual(dashboard["today"]["recommended_minutes"], 8)

    def test_live_bio_sample_drives_readiness(self):
        self.engine.ingest_bio(62, 58.5, 18)
        dashboard = self.engine.dashboard("Test User")
        self.assertTrue(dashboard["today"]["live_data"])
        self.assertNotEqual(dashboard["today"]["readiness"], "Connect device")
        self.assertEqual(dashboard["today"]["current_rmssd"], 58.5)

    def test_mood_informs_initial_agent_state(self):
        session = self.engine.begin(480, "drained", "Test User", "Polar H10")
        active = self.engine.sessions[session["session_id"]]
        self.assertEqual(active["initial_ai_state"], 1)
        self.assertIn(active["initial_audio_frequency"], self.engine.agent_for("Test User").actions)

    def test_learning_requires_completed_sessions(self):
        stats = self.engine.store.stats("Test User")
        stats.update(decisions=250, positive_responses=120, patterns=[30, 40, 50])
        self.engine.store.save_stats("Test User", stats)
        dashboard = self.engine.dashboard("Test User")
        self.assertEqual(dashboard["learning"]["percent"], 0)
        self.assertEqual(dashboard["learning"]["patterns_tested"], 0)


if __name__ == "__main__":
    unittest.main()
