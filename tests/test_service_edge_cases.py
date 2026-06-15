"""服务层边界条件和异常路径测试。

验证 ScholarService 在异常输入、缺失数据、边界条件下的行为，
对应测试文档中的 ET-01 至 ET-08 异常测试用例以及服务层边界用例。
"""

import tempfile
import unittest
from pathlib import Path

from app.scholar_service import ScholarService
from app.storage import JsonStore


class FakeLLM:
    def is_configured(self):
        return False


class FakeLowScaleLLM:
    """模拟模型返回低分值（0-1 范围）的场景。"""

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


class FakeFailLLM:
    """模拟模型调用抛出异常的场景。"""

    def is_configured(self):
        return True

    def chat_json_with_usage(self, system_prompt, user_prompt):
        raise RuntimeError("Model did not return valid JSON: unexpected output")


class ServiceFactory:
    """测试辅助：创建使用临时目录的 ScholarService。"""

    @staticmethod
    def create(llm=None):
        temp_dir = tempfile.TemporaryDirectory()
        service = ScholarService(JsonStore(Path(temp_dir.name)), llm or FakeLLM())
        return service, temp_dir


# ── ET-01: API Key 未配置时走 fallback ──


class FallbackAnalysisTests(unittest.TestCase):
    """未配置 API Key 时，AI 精读应走 fallback 路径。"""

    def test_analyze_uses_fallback_when_no_api_key(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)
        paper = service.create_paper({"title": "Fallback 测试", "abstract": "测试摘要"})

        result = service.analyze_paper(paper["id"])

        self.assertIn("analysis", result)
        self.assertIn("summary", result["analysis"])
        self.assertIn("keywords", result["analysis"])
        # fallback 分析应该包含引导性文字
        self.assertTrue(len(result["analysis"]["summary"]) > 0)


class FallbackPlanTests(unittest.TestCase):
    """未配置 API Key 时，研究计划应走 fallback 路径。"""

    def test_plan_uses_fallback_when_no_api_key(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        result = service.build_research_plan("深度学习优化", [])

        self.assertIn("topic_summary", result)
        self.assertIn("weekly_plan", result)
        self.assertGreaterEqual(len(result["weekly_plan"]), 1)


class FallbackWritingTests(unittest.TestCase):
    """未配置 API Key 时，写作包应走 fallback 路径。"""

    def test_writing_uses_fallback_when_no_api_key(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        result = service.generate_writing_pack("学术写作", [], "课程报告")

        self.assertIn("outline", result)
        self.assertIn("abstract_draft", result)


class FallbackAssistantTests(unittest.TestCase):
    """未配置 API Key 时，AI 问答应走 fallback 路径。"""

    def test_assistant_uses_fallback_when_no_api_key(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)
        paper = service.create_paper({"title": "问答测试", "abstract": "测试摘要"})

        result = service.assistant_chat(paper["id"], "这篇论文讲了什么？")

        self.assertIn("messages", result)
        # fallback 回答应该非空
        assistant_msg = [m for m in result["messages"] if m["role"] == "assistant"]
        self.assertTrue(len(assistant_msg) > 0)
        self.assertTrue(len(assistant_msg[0]["content"]) > 0)


# ── ET-04: 不存在的 paper_id 应抛出 ValueError ──


class MissingPaperTests(unittest.TestCase):
    """验证各方法对不存在论文的异常处理。"""

    def setUp(self):
        self.service, self.temp_dir = ServiceFactory.create()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_paper_raises_for_missing_id(self):
        with self.assertRaises(ValueError):
            self.service.get_paper("nonexistent-id-999")

    def test_analyze_paper_raises_for_missing_id(self):
        with self.assertRaises(ValueError):
            self.service.analyze_paper("nonexistent-id-999")

    def test_translate_paper_raises_for_missing_id(self):
        with self.assertRaises(ValueError):
            self.service.translate_paper("nonexistent-id-999", "zh", "abstract")

    def test_sentence_search_raises_for_missing_id(self):
        with self.assertRaises(ValueError):
            self.service.sentence_search("nonexistent-id-999", "关键词")

    def test_assistant_chat_raises_for_missing_id(self):
        with self.assertRaises(ValueError):
            self.service.assistant_chat("nonexistent-id-999", "问题")

    def test_get_challenge_raises_for_missing_id(self):
        with self.assertRaises(ValueError):
            self.service.get_challenge("nonexistent-id-999")

    def test_challenge_report_raises_for_missing_id(self):
        with self.assertRaises(ValueError):
            self.service.challenge_report("nonexistent-id-999")


# ── ET-05: 闯关空答案 / 无效关卡 ──


class ChallengeAnswerValidationTests(unittest.TestCase):
    """验证闯关答案提交的输入校验。"""

    def setUp(self):
        self.service, self.temp_dir = ServiceFactory.create()
        self.paper = self.service.create_paper(
            {
                "title": "闯关校验论文",
                "abstract": "测试摘要",
                "content": "正文内容",
                "analysis": {
                    "research_problem": "测试问题",
                    "method": "测试方法",
                    "limitations": ["局限一"],
                },
            }
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_answer_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.service.submit_challenge_answer(self.paper["id"], "problem", "")

    def test_whitespace_answer_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.service.submit_challenge_answer(self.paper["id"], "problem", "   ")

    def test_invalid_stage_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.service.submit_challenge_answer(
                self.paper["id"], "nonexistent-stage", "有效答案"
            )


# ── ET-06: AI 返回低分值时的归一化 ──


class ScoreNormalizationTests(unittest.TestCase):
    """验证闯关评分归一化逻辑的各种边界情况。"""

    def test_score_1_with_pass_level_becomes_80_plus(self):
        """模型返回 score=1, level=pass 时，归一化后应 >=80。"""
        service, temp_dir = ServiceFactory.create(FakeLowScaleLLM())
        self.addCleanup(temp_dir.cleanup)
        paper = service.create_paper(
            {
                "title": "归一化测试",
                "abstract": "测试",
                "content": "内容",
                "analysis": {"research_problem": "问题", "method": "方法", "limitations": []},
            }
        )
        run = service.submit_challenge_answer(paper["id"], "problem", "这是一段有效回答")
        self.assertGreaterEqual(run["stages"][0]["latest_attempt"]["score"], 80)

    def test_fallback_score_is_reasonable(self):
        """未配置 API 时，fallback 评分应在合理范围内。"""
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)
        paper = service.create_paper(
            {
                "title": "Fallback 评分测试",
                "abstract": "测试",
                "content": "内容",
                "analysis": {"research_problem": "问题", "method": "方法", "limitations": []},
            }
        )
        run = service.submit_challenge_answer(
            paper["id"], "problem", "这篇论文解决了一个重要的研究问题"
        )
        score = run["stages"][0]["latest_attempt"]["score"]
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


# ── AI 调用异常时走 fallback ──


class LLMExceptionFallbackTests(unittest.TestCase):
    """模型调用抛出异常时应降级到 fallback。"""

    def test_analyze_falls_back_on_llm_error(self):
        service, temp_dir = ServiceFactory.create(FakeFailLLM())
        self.addCleanup(temp_dir.cleanup)
        paper = service.create_paper({"title": "异常降级测试", "abstract": "摘要"})

        result = service.analyze_paper(paper["id"])

        self.assertIn("analysis", result)
        # 应该走 fallback 路径，而不是抛异常
        self.assertIn("summary", result["analysis"])


# ── 课堂汇报边界情况 ──


class ChallengeReportEdgeTests(unittest.TestCase):
    """课堂汇报边界情况测试。"""

    def test_report_with_zero_completed_stages(self):
        """未提交任何闯关答案时，汇报应能正常生成。"""
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)
        paper = service.create_paper(
            {
                "title": "零完成汇报",
                "abstract": "测试",
                "content": "内容",
                "analysis": {"research_problem": "问题", "method": "方法", "limitations": []},
            }
        )
        # 先创建闯关（不提交答案）
        service.get_challenge(paper["id"])

        report = service.challenge_report(paper["id"])

        self.assertEqual(report["overall_score"], 0)
        self.assertIn("建议继续补完闯关答案", report["readiness"])
        self.assertGreaterEqual(len(report["sections"]), 5)


# ── 检索历史恢复异常 ──


class RestoreSearchHistoryTests(unittest.TestCase):
    """验证检索历史恢复的异常处理。"""

    def test_restore_missing_history_raises_value_error(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        with self.assertRaises(ValueError):
            service.restore_search_history("nonexistent-history-id")


# ── 句子检索边界情况 ──


class SentenceSearchEdgeTests(unittest.TestCase):
    """句子检索边界情况测试。"""

    def setUp(self):
        self.service, self.temp_dir = ServiceFactory.create()
        self.paper = self.service.create_paper(
            {
                "title": "句子检索测试",
                "content": "深度学习是机器学习的一个分支。它使用多层神经网络来学习数据的表示。近年来Transformer架构取得了成功。",
            }
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_matching_query_returns_results(self):
        result = self.service.sentence_search(self.paper["id"], "深度学习")
        self.assertGreater(len(result["matches"]), 0)

    def test_non_matching_query_returns_empty(self):
        result = self.service.sentence_search(self.paper["id"], "量子计算超导材料")
        self.assertEqual(len(result["matches"]), 0)


# ── 仪表盘空数据 ──


class DashboardEmptyTests(unittest.TestCase):
    """验证空数据时仪表盘正常返回。"""

    def test_dashboard_with_no_data(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        result = service.dashboard()

        self.assertEqual(result["paper_count"], 0)
        self.assertEqual(result["note_count"], 0)
        self.assertEqual(len(result["papers"]), 0)
        self.assertEqual(len(result["notes"]), 0)


# ── 笔记保存默认值 ──


class NoteDefaultsTests(unittest.TestCase):
    """验证笔记保存时缺失字段的默认值。"""

    def setUp(self):
        self.service, self.temp_dir = ServiceFactory.create()
        self.paper = self.service.create_paper({"title": "笔记默认值测试"})

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_note_defaults_kind_to_manual(self):
        note = self.service.save_note(
            {"paper_id": self.paper["id"], "content": "只有内容"}
        )
        self.assertEqual(note["kind"], "manual")

    def test_note_defaults_title_when_empty(self):
        note = self.service.save_note(
            {"paper_id": self.paper["id"], "title": "", "content": "内容"}
        )
        self.assertEqual(note["title"], "阅读笔记")

    def test_note_defaults_empty_strings_for_optional_fields(self):
        note = self.service.save_note(
            {"paper_id": self.paper["id"], "content": "内容"}
        )
        self.assertEqual(note["source_text"], "")
        self.assertEqual(note["page_label"], "")
        self.assertEqual(note["anchor_text"], "")
        self.assertEqual(note["ai_prompt"], "")


# ── 翻译功能边界 ──


class TranslateEdgeTests(unittest.TestCase):
    """翻译功能边界情况测试。"""

    def setUp(self):
        self.service, self.temp_dir = ServiceFactory.create()
        self.paper = self.service.create_paper(
            {
                "title": "Translation Test Paper",
                "abstract": "This paper studies the application of deep learning.",
            }
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_translate_with_fallback_returns_result(self):
        result = self.service.translate_paper(self.paper["id"], "zh", "abstract")
        self.assertIn("translated_text", result)
        # fallback 时直接返回原文
        self.assertTrue(len(result["translated_text"]) > 0)

    def test_translate_scope_title(self):
        result = self.service.translate_paper(self.paper["id"], "zh", "title")
        self.assertEqual(result["scope"], "title")


# ── 论文创建/更新 ──


class CreatePaperEdgeTests(unittest.TestCase):
    """论文创建和更新的边界情况测试。"""

    def setUp(self):
        self.service, self.temp_dir = ServiceFactory.create()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_paper_auto_generates_id(self):
        paper = self.service.create_paper({"title": "自动 ID 测试"})
        self.assertTrue(len(paper["id"]) > 0)

    def test_create_paper_with_existing_id_updates(self):
        first = self.service.create_paper(
            {"title": "原始标题", "authors": "张三"}
        )
        second = self.service.create_paper(
            {"id": first["id"], "title": "更新标题", "authors": "李四"}
        )
        self.assertEqual(second["title"], "更新标题")
        self.assertEqual(second["authors"], "李四")
        # 应该是更新而不是新增
        self.assertEqual(len(self.service.store.list_papers()), 1)

    def test_create_paper_preserves_pages_on_update(self):
        first = self.service.create_paper(
            {"title": "有页面", "pages": ["第一页", "第二页"], "analysis": {"summary": "摘要"}}
        )
        second = self.service.create_paper(
            {"id": first["id"], "title": "更新标题"}
        )
        self.assertEqual(second["pages"], ["第一页", "第二页"])


# ── 检索功能边界 ──


class SearchTopicEdgeTests(unittest.TestCase):
    """检索功能边界情况测试。"""

    def test_search_returns_results_with_fallback(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        result = service.search_topic("transformer")

        self.assertIn("keywords", result)
        self.assertIn("results", result)
        self.assertGreater(len(result["results"]), 0)

    def test_search_returns_search_links(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        result = service.search_topic("deep learning")

        self.assertIn("search_links", result)
        links = result["search_links"]
        self.assertIn("arxiv", links)
        self.assertIn("google_scholar", links)

    def test_search_saves_history(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        service.search_topic("检索历史测试")
        history = service.store.list_search_history()

        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]["query"], "检索历史测试")


# ── 研究计划和写作包边界 ──


class ResearchPlanEdgeTests(unittest.TestCase):
    """研究计划边界情况测试。"""

    def test_plan_with_empty_paper_list(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        result = service.build_research_plan("测试主题", [])

        self.assertIn("topic_summary", result)
        self.assertIn("weekly_plan", result)


class WritingPackEdgeTests(unittest.TestCase):
    """写作包边界情况测试。"""

    def test_writing_pack_with_empty_inputs(self):
        service, temp_dir = ServiceFactory.create()
        self.addCleanup(temp_dir.cleanup)

        result = service.generate_writing_pack("测试主题", [], "测试目标")

        self.assertIn("outline", result)
        self.assertIn("abstract_draft", result)
        self.assertIn("writing_tips", result)


if __name__ == "__main__":
    unittest.main()
