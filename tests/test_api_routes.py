"""FastAPI 接口自动化测试。

使用 FastAPI TestClient 验证各 API 端点的正常响应和错误处理，
对应测试文档中的 API-01 至 API-11 以及部分 ET 异常测试用例。
"""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import create_app
from app.deepseek_client import DeepSeekClient
from app.scholar_service import ScholarService
from app.storage import JsonStore


class FakeLLM:
    """未配置 API Key 的 LLM 替身，使服务走 fallback 路径。"""

    model = "test-model"

    def is_configured(self):
        return False


def _make_test_app():
    """创建使用临时数据目录和 FakeLLM 的测试应用。"""
    temp_dir = tempfile.TemporaryDirectory()

    test_store = JsonStore(Path(temp_dir.name))
    test_llm = FakeLLM()
    test_scholar = ScholarService(test_store, test_llm)

    from app.main import create_router
    from fastapi import FastAPI

    app = FastAPI()
    router = create_router(test_store, test_llm, test_scholar)
    app.include_router(router)

    client = TestClient(app)
    return client, test_store, test_scholar, test_llm, temp_dir


class APIStatusTests(unittest.TestCase):
    """API-01: GET /api/status"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_status_returns_200(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)

    def test_status_contains_configured_field(self):
        data = self.client.get("/api/status").json()
        self.assertIn("configured", data)
        self.assertFalse(data["configured"])

    def test_status_contains_model_field(self):
        data = self.client.get("/api/status").json()
        self.assertIn("model", data)

    def test_status_contains_storage_stats(self):
        data = self.client.get("/api/status").json()
        self.assertIn("paper_count", data)
        self.assertIn("note_count", data)


class APIDashboardTests(unittest.TestCase):
    """API-02: GET /api/dashboard"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_dashboard_returns_200(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_contains_expected_collections(self):
        data = self.client.get("/api/dashboard").json()
        for key in ("papers", "notes", "search_history", "plans", "writing_drafts"):
            self.assertIn(key, data)


class APITutorialSampleTests(unittest.TestCase):
    """API-03: POST /api/tutorial/sample-paper"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_sample_paper_returns_200(self):
        response = self.client.post("/api/tutorial/sample-paper")
        self.assertEqual(response.status_code, 200)

    def test_sample_paper_has_expected_fields(self):
        data = self.client.post("/api/tutorial/sample-paper").json()
        self.assertTrue(data.get("tutorial_sample"))
        self.assertIn("analysis", data)
        self.assertIn("pages", data)

    def test_sample_paper_idempotent(self):
        first = self.client.post("/api/tutorial/sample-paper").json()
        second = self.client.post("/api/tutorial/sample-paper").json()
        self.assertEqual(first["id"], second["id"])


class APICreatePaperTests(unittest.TestCase):
    """POST /api/papers 创建论文接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_create_paper_returns_200(self):
        response = self.client.post(
            "/api/papers",
            json={"title": "测试论文", "authors": "张三", "year": "2026"},
        )
        self.assertEqual(response.status_code, 200)

    def test_create_paper_preserves_fields(self):
        data = self.client.post(
            "/api/papers",
            json={"title": "字段保留测试", "authors": "李四", "year": "2025", "abstract": "测试摘要"},
        ).json()
        self.assertEqual(data["title"], "字段保留测试")
        self.assertEqual(data["authors"], "李四")
        self.assertEqual(data["year"], "2025")

    def test_create_paper_empty_title_returns_422(self):
        """FastAPI Pydantic 校验：空字符串不满足 min_length=1，返回 422。"""
        response = self.client.post("/api/papers", json={"title": ""})
        self.assertEqual(response.status_code, 422)

    def test_create_paper_missing_title_returns_422(self):
        """FastAPI Pydantic 校验：缺少必填字段，返回 422。"""
        response = self.client.post("/api/papers", json={})
        self.assertEqual(response.status_code, 422)

    def test_create_paper_whitespace_title_returns_422(self):
        """FastAPI Pydantic 校验：纯空格不满足 min_length=1，返回 422。"""
        response = self.client.post("/api/papers", json={"title": "   "})
        self.assertEqual(response.status_code, 422)


class APIGetPaperTests(unittest.TestCase):
    """GET /api/papers/<paper_id> 获取论文接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()
        cls.paper = cls.client.post(
            "/api/papers",
            json={"title": "获取测试论文", "authors": "王五"},
        ).json()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_get_existing_paper_returns_200(self):
        response = self.client.get(f"/api/papers/{self.paper['id']}")
        self.assertEqual(response.status_code, 200)

    def test_get_existing_paper_has_title(self):
        data = self.client.get(f"/api/papers/{self.paper['id']}").json()
        self.assertEqual(data["title"], "获取测试论文")

    def test_get_missing_paper_returns_404(self):
        response = self.client.get("/api/papers/nonexistent-id-12345")
        self.assertEqual(response.status_code, 404)


class APIAnalyzePaperTests(unittest.TestCase):
    """API-05: POST /api/papers/<id>/analyze AI 精读接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()
        cls.paper = cls.client.post(
            "/api/papers",
            json={"title": "分析测试论文", "abstract": "本文研究深度学习在自然语言处理中的应用。"},
        ).json()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_analyze_with_fallback_returns_200(self):
        response = self.client.post(f"/api/papers/{self.paper['id']}/analyze")
        self.assertEqual(response.status_code, 200)

    def test_analyze_returns_analysis_fields(self):
        data = self.client.post(f"/api/papers/{self.paper['id']}/analyze").json()
        self.assertIn("analysis", data)
        analysis = data["analysis"]
        self.assertIn("summary", analysis)
        self.assertIn("keywords", analysis)
        self.assertIn("research_problem", analysis)

    def test_analyze_missing_paper_returns_404(self):
        response = self.client.post("/api/papers/nonexistent-id/analyze")
        self.assertEqual(response.status_code, 404)


class APIChallengeTests(unittest.TestCase):
    """API-06/07: 闯关相关接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()
        cls.paper = cls.client.post(
            "/api/papers",
            json={
                "title": "闯关测试论文",
                "abstract": "本文研究无人机巡检中的电磁安全与路径优化问题。",
                "content": "摘要：本文研究无人机巡检中的电磁安全与路径优化问题。方法包括点云采集、电磁仿真和遗传算法路径优化。",
                "analysis": {
                    "research_problem": "如何在电磁安全约束下优化无人机巡检路径。",
                    "method": "先采集点云，再做电磁仿真，最后用遗传算法优化路径。",
                    "limitations": ["依赖高质量点云", "动态环境考虑不足"],
                },
            },
        ).json()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_get_challenge_returns_5_stages(self):
        data = self.client.get(f"/api/papers/{self.paper['id']}/challenge").json()
        self.assertEqual(data["total_count"], 5)
        self.assertEqual(len(data["stages"]), 5)

    def test_get_challenge_first_stage_is_problem(self):
        data = self.client.get(f"/api/papers/{self.paper['id']}/challenge").json()
        self.assertEqual(data["stages"][0]["id"], "problem")

    def test_submit_answer_returns_score(self):
        data = self.client.post(
            f"/api/papers/{self.paper['id']}/challenge/problem",
            json={"answer": "这篇论文解决无人机巡检中电磁干扰导致的安全风险。"},
        ).json()
        self.assertIn("stages", data)
        self.assertGreaterEqual(data["stages"][0]["latest_attempt"]["score"], 0)

    def test_submit_empty_answer_returns_422(self):
        """Pydantic min_length=1 校验：空答案返回 422。"""
        response = self.client.post(
            f"/api/papers/{self.paper['id']}/challenge/problem",
            json={"answer": ""},
        )
        self.assertEqual(response.status_code, 422)

    def test_submit_whitespace_answer_returns_422(self):
        """Pydantic min_length=1 校验：纯空格答案返回 422。"""
        response = self.client.post(
            f"/api/papers/{self.paper['id']}/challenge/problem",
            json={"answer": "   "},
        )
        self.assertEqual(response.status_code, 422)

    def test_challenge_missing_paper_returns_404(self):
        response = self.client.get("/api/papers/nonexistent-id/challenge")
        self.assertEqual(response.status_code, 404)


class APIChallengeReportTests(unittest.TestCase):
    """API-08: GET /api/papers/<id>/challenge-report 课堂汇报接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()
        cls.paper = cls.client.post(
            "/api/papers",
            json={
                "title": "汇报测试论文",
                "abstract": "本文研究强化学习在机器人控制中的应用。",
                "content": "方法包括状态空间建模、奖励函数设计和策略梯度优化。",
                "analysis": {
                    "research_problem": "如何设计高效的奖励函数使机器人学会复杂任务。",
                    "method": "状态空间建模、奖励函数设计、策略梯度优化。",
                    "limitations": ["奖励函数设计依赖专家经验", "仿真环境与真实环境存在差距"],
                },
            },
        ).json()
        cls.client.post(
            f"/api/papers/{cls.paper['id']}/challenge/problem",
            json={"answer": "本文解决机器人奖励函数设计效率问题。"},
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_challenge_report_returns_200(self):
        response = self.client.get(f"/api/papers/{self.paper['id']}/challenge-report")
        self.assertEqual(response.status_code, 200)

    def test_challenge_report_has_sections(self):
        data = self.client.get(f"/api/papers/{self.paper['id']}/challenge-report").json()
        self.assertIn("sections", data)
        self.assertGreaterEqual(len(data["sections"]), 5)

    def test_challenge_report_has_overall_score(self):
        data = self.client.get(f"/api/papers/{self.paper['id']}/challenge-report").json()
        self.assertIn("overall_score", data)


class APINotesTests(unittest.TestCase):
    """API-09: POST /api/notes 笔记接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()
        cls.paper = cls.client.post(
            "/api/papers",
            json={"title": "笔记测试论文"},
        ).json()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_save_note_returns_200(self):
        response = self.client.post(
            "/api/notes",
            json={
                "paper_id": self.paper["id"],
                "title": "阅读笔记",
                "content": "这篇论文的核心贡献是...",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_save_note_preserves_content(self):
        data = self.client.post(
            "/api/notes",
            json={
                "paper_id": self.paper["id"],
                "title": "方法笔记",
                "content": "方法流程包括数据采集和模型训练。",
            },
        ).json()
        self.assertEqual(data["content"], "方法流程包括数据采集和模型训练。")

    def test_save_note_missing_paper_id_returns_422(self):
        """Pydantic 校验：缺少 paper_id 返回 422。"""
        response = self.client.post(
            "/api/notes",
            json={"title": "无论文笔记", "content": "内容"},
        )
        self.assertEqual(response.status_code, 422)

    def test_save_note_empty_paper_id_returns_422(self):
        """Pydantic min_length=1 校验：空 paper_id 返回 422。"""
        response = self.client.post(
            "/api/notes",
            json={"paper_id": "", "title": "空论文", "content": "内容"},
        )
        self.assertEqual(response.status_code, 422)


class APIDiscoverySearchTests(unittest.TestCase):
    """POST /api/discovery/search 检索接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_search_with_topic_returns_200(self):
        response = self.client.post(
            "/api/discovery/search",
            json={"topic": "transformer attention"},
        )
        self.assertEqual(response.status_code, 200)

    def test_search_returns_keywords_and_results(self):
        data = self.client.post(
            "/api/discovery/search",
            json={"topic": "large language model"},
        ).json()
        self.assertIn("keywords", data)
        self.assertIn("results", data)

    def test_search_empty_topic_returns_422(self):
        """Pydantic min_length=1 校验：空 topic 返回 422。"""
        response = self.client.post(
            "/api/discovery/search",
            json={"topic": ""},
        )
        self.assertEqual(response.status_code, 422)

    def test_search_whitespace_topic_returns_422(self):
        """Pydantic min_length=1 校验：纯空格 topic 返回 422。"""
        response = self.client.post(
            "/api/discovery/search",
            json={"topic": "   "},
        )
        self.assertEqual(response.status_code, 422)


class APIDiscoverySaveResultTests(unittest.TestCase):
    """POST /api/discovery/save-result 保存检索结果接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_save_result_empty_title_returns_422(self):
        """Pydantic min_length=1 校验：空 title 返回 422。"""
        response = self.client.post(
            "/api/discovery/save-result",
            json={"title": "", "authors": "A", "year": "2024"},
        )
        self.assertEqual(response.status_code, 422)


class APIResearchPlanTests(unittest.TestCase):
    """API-10: POST /api/research-plan 研究计划接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_plan_with_fallback_returns_200(self):
        response = self.client.post(
            "/api/research-plan",
            json={"topic": "深度学习优化"},
        )
        self.assertEqual(response.status_code, 200)

    def test_plan_returns_expected_fields(self):
        data = self.client.post(
            "/api/research-plan",
            json={"topic": "自然语言处理"},
        ).json()
        self.assertIn("topic_summary", data)
        self.assertIn("weekly_plan", data)

    def test_plan_empty_topic_returns_422(self):
        """Pydantic min_length=1 校验：空 topic 返回 422。"""
        response = self.client.post(
            "/api/research-plan",
            json={"topic": ""},
        )
        self.assertEqual(response.status_code, 422)


class APIWritingPackTests(unittest.TestCase):
    """API-11: POST /api/writing-pack 写作包接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_writing_pack_with_fallback_returns_200(self):
        response = self.client.post(
            "/api/writing-pack",
            json={"topic": "学术写作", "goal": "课程报告"},
        )
        self.assertEqual(response.status_code, 200)

    def test_writing_pack_returns_expected_fields(self):
        data = self.client.post(
            "/api/writing-pack",
            json={"topic": "论文综述", "goal": "综述报告"},
        ).json()
        self.assertIn("outline", data)
        self.assertIn("abstract_draft", data)

    def test_writing_pack_empty_topic_returns_422(self):
        """Pydantic min_length=1 校验：空 topic 返回 422。"""
        response = self.client.post(
            "/api/writing-pack",
            json={"topic": "", "goal": "报告"},
        )
        self.assertEqual(response.status_code, 422)


class APISentenceSearchTests(unittest.TestCase):
    """POST /api/papers/<id>/sentence-search 句子检索接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()
        cls.paper = cls.client.post(
            "/api/papers",
            json={
                "title": "句子搜索测试",
                "content": "深度学习是机器学习的一个分支。它使用多层神经网络来学习数据的表示。近年来，Transformer架构在自然语言处理领域取得了巨大成功。",
            },
        ).json()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_sentence_search_returns_matches(self):
        data = self.client.post(
            f"/api/papers/{self.paper['id']}/sentence-search",
            json={"query": "深度学习"},
        ).json()
        self.assertIn("matches", data)

    def test_sentence_search_empty_query_returns_422(self):
        """Pydantic min_length=1 校验：空 query 返回 422。"""
        response = self.client.post(
            f"/api/papers/{self.paper['id']}/sentence-search",
            json={"query": ""},
        )
        self.assertEqual(response.status_code, 422)

    def test_sentence_search_missing_paper_returns_404(self):
        response = self.client.post(
            "/api/papers/nonexistent-id/sentence-search",
            json={"query": "test"},
        )
        self.assertEqual(response.status_code, 404)


class APIAssistantTests(unittest.TestCase):
    """POST /api/papers/<id>/assistant AI 问答接口测试"""

    @classmethod
    def setUpClass(cls):
        cls.client, cls.store, cls.scholar, cls.llm, cls.temp_dir = _make_test_app()
        cls.paper = cls.client.post(
            "/api/papers",
            json={"title": "问答测试论文", "abstract": "本文研究知识图谱的构建方法。"},
        ).json()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_assistant_with_fallback_returns_200(self):
        response = self.client.post(
            f"/api/papers/{self.paper['id']}/assistant",
            json={"message": "这篇论文的核心贡献是什么？"},
        )
        self.assertEqual(response.status_code, 200)

    def test_assistant_returns_messages(self):
        data = self.client.post(
            f"/api/papers/{self.paper['id']}/assistant",
            json={"message": "请解释研究问题"},
        ).json()
        self.assertIn("messages", data)

    def test_assistant_empty_message_returns_422(self):
        """Pydantic min_length=1 校验：空 message 返回 422。"""
        response = self.client.post(
            f"/api/papers/{self.paper['id']}/assistant",
            json={"message": ""},
        )
        self.assertEqual(response.status_code, 422)

    def test_assistant_missing_paper_returns_404(self):
        response = self.client.post(
            "/api/papers/nonexistent-id/assistant",
            json={"message": "test"},
        )
        self.assertEqual(response.status_code, 404)

    def test_translate_missing_paper_returns_404(self):
        response = self.client.post(
            "/api/papers/nonexistent-id/translate",
            json={"target_language": "zh", "scope": "abstract"},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
