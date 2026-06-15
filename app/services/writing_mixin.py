"""写作与研究计划服务 Mixin。

包含研究计划生成、写作包生成等逻辑。
依赖 self.store 和 self.llm_client（由 ScholarService 设置）。
"""

from typing import Any, Dict, List

from .constants import PLAN_PROMPT, WRITING_PROMPT
from .helpers import (
    fallback_plan,
    fallback_writing,
    now,
    notes_context,
    paper_context,
)


class WritingMixin:
    """写作与研究计划相关的方法。

    需要 self.store (JsonStore) 和 self.llm_client (DeepSeekClient)。
    """

    def build_research_plan(self, topic: str, selected_paper_ids: List[str]) -> Dict[str, Any]:
        papers = [self.store.get_paper(item) for item in selected_paper_ids]
        papers = [item for item in papers if item]
        context = paper_context(papers)
        prompt = f"Research topic: {topic}\n\nSelected papers:\n{context}"
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(PLAN_PROMPT, prompt)
            except Exception:
                result = fallback_plan(topic, papers)
        else:
            result = fallback_plan(topic, papers)

        record = {
            "topic": topic,
            "paper_ids": selected_paper_ids,
            "result": result,
            "created_at": now(),
        }
        saved = self.store.save_plan(record)
        return {"id": saved["id"], **result}

    def generate_writing_pack(self, topic: str, selected_paper_ids: List[str], writing_goal: str) -> Dict[str, Any]:
        papers = [self.store.get_paper(item) for item in selected_paper_ids]
        papers = [item for item in papers if item]
        notes = []
        for paper in papers:
            notes.extend(self.store.list_notes_for_paper(paper["id"]))
        prompt = (
            f"Topic: {topic}\n"
            f"Writing goal: {writing_goal}\n\n"
            f"Papers:\n{paper_context(papers)}\n\n"
            f"Notes:\n{notes_context(notes)}"
        )
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(WRITING_PROMPT, prompt)
            except Exception:
                result = fallback_writing(topic, papers, notes, writing_goal)
        else:
            result = fallback_writing(topic, papers, notes, writing_goal)

        record = {
            "topic": topic,
            "goal": writing_goal,
            "paper_ids": selected_paper_ids,
            "result": result,
            "created_at": now(),
        }
        saved = self.store.save_writing_draft(record)
        return {"id": saved["id"], **result}
