import tempfile
import unittest
from pathlib import Path

from app.scholar_service import ScholarService
from app.storage import JsonStore


class FakeLLM:
    def is_configured(self):
        return False


class FakeLowScaleLLM:
    def is_configured(self):
        return True

    def chat_json_with_usage(self, system_prompt, user_prompt):
        return {
            "score": 1,
            "level": "pass",
            "feedback": "Answer is broadly correct.",
            "correction": "Corrected answer.",
            "evidence_hint": "Check the abstract.",
            "next_task": "Continue to the next stage.",
        }, {}


class ChallengeFlowTests(unittest.TestCase):
    def make_service(self, llm=None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        service = ScholarService(JsonStore(Path(temp_dir.name)), llm or FakeLLM())
        paper = service.create_paper(
            {
                "id": "paper-1",
                "title": "测试论文",
                "authors": "A",
                "year": "2026",
                "source": "Demo",
                "abstract": "本文研究无人机巡检中的电磁安全与路径优化问题。",
                "content": "摘要：本文研究无人机巡检中的电磁安全与路径优化问题。方法包括点云采集、电磁仿真和遗传算法路径优化。实验图表展示路径缩短和安全距离。",
                "analysis": {
                    "research_problem": "如何在电磁安全约束下优化无人机巡检路径。",
                    "method": "先采集点云，再做电磁仿真，最后用遗传算法优化路径。",
                    "limitations": ["依赖高质量点云", "动态环境考虑不足"],
                },
            }
        )
        return service, paper

    def test_get_challenge_creates_five_training_stages(self):
        service, paper = self.make_service()

        run = service.get_challenge(paper["id"])

        self.assertEqual(run["total_count"], 5)
        self.assertEqual(run["completed_count"], 0)
        self.assertEqual(run["stages"][0]["id"], "problem")

    def test_submit_answer_persists_score_and_report(self):
        service, paper = self.make_service()

        run = service.submit_challenge_answer(
            paper["id"],
            "problem",
            "这篇论文解决无人机巡检中电磁干扰导致的安全风险，并希望优化巡检路径效率。",
        )
        report = service.challenge_report(paper["id"])

        self.assertGreaterEqual(run["stages"][0]["latest_attempt"]["score"], 60)
        self.assertEqual(run["completed_count"], 1)
        self.assertEqual(report["paper_title"], "测试论文")
        self.assertEqual(report["sections"][0]["title"], "研究问题")

    def test_model_one_point_pass_score_is_normalized(self):
        service, paper = self.make_service(FakeLowScaleLLM())

        run = service.submit_challenge_answer(
            paper["id"],
            "problem",
            "这篇论文解决无人机巡检中电磁干扰导致的安全风险，并希望优化巡检路径效率。",
        )

        attempt = run["stages"][0]["latest_attempt"]
        report = service.challenge_report(paper["id"])

        self.assertGreaterEqual(attempt["score"], 80)
        self.assertEqual(run["completed_count"], 1)
        self.assertGreaterEqual(report["overall_score"], 80)


if __name__ == "__main__":
    unittest.main()
