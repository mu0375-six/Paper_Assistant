import tempfile
import unittest
from pathlib import Path

from app.scholar_service import ScholarService
from app.storage import JsonStore


class FakeLLM:
    model = "test-model"

    def is_configured(self):
        return False


class TutorialSampleTests(unittest.TestCase):
    def test_sample_paper_is_idempotent_and_ready_for_guided_reading(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        service = ScholarService(JsonStore(Path(temp_dir.name)), FakeLLM())

        first = service.ensure_sample_paper()
        second = service.ensure_sample_paper()

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(service.store.list_papers()), 1)
        self.assertTrue(first["tutorial_sample"])
        self.assertGreaterEqual(len(first["pages"]), 3)
        self.assertIn("research_problem", first["analysis"])
        self.assertGreaterEqual(len(first["analysis"]["reading_questions"]), 3)


if __name__ == "__main__":
    unittest.main()
