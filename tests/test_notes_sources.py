import tempfile
import unittest
from pathlib import Path

from app.scholar_service import ScholarService
from app.storage import JsonStore


class FakeLLM:
    model = "test-model"

    def is_configured(self):
        return False


class NoteSourceTests(unittest.TestCase):
    def make_service(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return ScholarService(JsonStore(Path(temp_dir.name)), FakeLLM())

    def test_save_note_preserves_pdf_selection_source(self):
        service = self.make_service()

        note = service.save_note(
            {
                "paper_id": "paper-1",
                "title": "选区解释",
                "content": "这段文字说明了研究问题。",
                "kind": "selection",
                "source_text": "本文提出一种融合激光点云和电磁安全约束的方法。",
                "page_label": "第 2 页",
                "anchor_text": "融合激光点云",
            }
        )

        self.assertEqual(note["kind"], "selection")
        self.assertEqual(note["source_text"], "本文提出一种融合激光点云和电磁安全约束的方法。")
        self.assertEqual(note["page_label"], "第 2 页")
        self.assertEqual(note["anchor_text"], "融合激光点云")

    def test_save_note_preserves_assistant_message_source(self):
        service = self.make_service()

        note = service.save_note(
            {
                "paper_id": "paper-1",
                "title": "AI 回答：方法流程",
                "content": "方法流程包括点云采集、电磁仿真和路径优化。",
                "kind": "assistant",
                "assistant_message_id": "msg-1",
                "ai_prompt": "请解释方法流程",
                "source_text": "AI 生成的课堂展示回答",
            }
        )

        self.assertEqual(note["kind"], "assistant")
        self.assertEqual(note["assistant_message_id"], "msg-1")
        self.assertEqual(note["ai_prompt"], "请解释方法流程")
        self.assertEqual(note["source_text"], "AI 生成的课堂展示回答")


if __name__ == "__main__":
    unittest.main()
