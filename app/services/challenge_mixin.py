"""闯关训练服务 Mixin。

包含闯关获取、答案提交、评分、课堂汇报等逻辑。
依赖 self.store 和 self.llm_client（由 ScholarService 设置）。
"""

from typing import Any, Dict

from .constants import CHALLENGE_PROMPT, CHALLENGE_STAGES
from .helpers import (
    fallback_analysis,
    fallback_challenge_evaluation,
    normalize_challenge_score,
    now,
    report_answer,
    stage_latest_attempt,
    with_challenge_progress,
)


class ChallengeMixin:
    """闯关训练相关的方法。

    需要 self.store (JsonStore) 和 self.llm_client (DeepSeekClient)。
    同时依赖 PaperMixin 的 get_paper 方法（通过 self 调用）。
    """

    def get_challenge(self, paper_id: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        runs = sorted(self.store.list_challenge_runs_for_paper(paper_id), key=lambda item: item.get("updated_at", ""), reverse=True)
        if runs:
            return with_challenge_progress(runs[0], paper)

        _now = now()
        run = {
            "id": "",
            "paper_id": paper_id,
            "paper_title": paper.get("title", ""),
            "stages": [{**stage, "attempts": []} for stage in CHALLENGE_STAGES],
            "created_at": _now,
            "updated_at": _now,
        }
        return with_challenge_progress(self.store.save_challenge_run(run), paper)

    def submit_challenge_answer(self, paper_id: str, stage_id: str, answer: str) -> Dict[str, Any]:
        if not answer.strip():
            raise ValueError("answer is required.")
        paper = self.get_paper(paper_id)
        run = self.get_challenge(paper_id)
        stage = next((item for item in run["stages"] if item["id"] == stage_id), None)
        if not stage:
            raise ValueError("Challenge stage not found.")

        evaluation = self._evaluate_challenge_answer(paper, stage, answer)
        attempt = {
            "answer": answer.strip(),
            "score": int(max(0, min(100, evaluation.get("score", 0)))),
            "level": evaluation.get("level", "needs_work"),
            "feedback": (evaluation.get("feedback") or "").strip(),
            "correction": (evaluation.get("correction") or "").strip(),
            "evidence_hint": (evaluation.get("evidence_hint") or "").strip(),
            "next_task": (evaluation.get("next_task") or "").strip(),
            "created_at": now(),
        }

        for item in run["stages"]:
            if item["id"] == stage_id:
                item.setdefault("attempts", []).append(attempt)
                break
        run["updated_at"] = now()
        saved = self.store.save_challenge_run(run)
        return with_challenge_progress(saved, paper)

    def challenge_report(self, paper_id: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        run = self.get_challenge(paper_id)
        latest = [stage_latest_attempt(stage) for stage in run["stages"]]
        completed = [item for item in latest if item]
        average = round(sum(item["score"] for item in completed) / len(completed), 1) if completed else 0
        analysis = paper.get("analysis") or fallback_analysis(paper)

        sections = [
            {"title": "研究问题", "content": report_answer(run, "problem", analysis.get("research_problem", "需要进一步明确研究问题。"))},
            {"title": "方法流程", "content": report_answer(run, "method", analysis.get("method", "需要进一步梳理方法流程。"))},
            {"title": "图表证据", "content": report_answer(run, "evidence", "建议结合关键图表说明论文证据链。")},
            {"title": "局限与质疑", "content": report_answer(run, "limits", "建议补充局限性与适用边界。")},
            {"title": "延伸问题", "content": report_answer(run, "extension", "建议提出可操作的后续研究问题。")},
        ]
        strengths = [stage["skill"] for stage in run["stages"] if (stage_latest_attempt(stage) or {}).get("score", 0) >= 80]
        improvements = [stage["skill"] for stage in run["stages"] if not stage_latest_attempt(stage) or (stage_latest_attempt(stage) or {}).get("score", 0) < 70]
        return {
            "paper_id": paper_id,
            "paper_title": paper.get("title", ""),
            "overall_score": average,
            "readiness": "可以用于课堂汇报" if average >= 75 else "建议继续补完闯关答案",
            "sections": sections,
            "strengths": strengths or ["已完成结构化阅读训练"],
            "improvements": improvements or ["可以继续补充原文证据和图表细节"],
            "updated_at": run.get("updated_at", ""),
        }

    # ── 内部方法 ───────────────────────────────────────────

    def _evaluate_challenge_answer(self, paper: Dict[str, Any], stage: Dict[str, Any], answer: str) -> Dict[str, Any]:
        fb = fallback_challenge_evaluation(paper, stage, answer)
        if self.llm_client.is_configured():
            prompt = (
                f"Paper title: {paper.get('title', '')}\n"
                f"Abstract: {paper.get('abstract', '')}\n"
                f"Analysis: {paper.get('analysis', {})}\n"
                f"Content excerpt:\n{paper.get('content', '')[:6500]}\n\n"
                f"Challenge: {stage.get('title')} / {stage.get('prompt')}\n"
                f"Student answer: {answer}"
            )
            try:
                result, _usage = self.llm_client.chat_json_with_usage(CHALLENGE_PROMPT, prompt)
                if isinstance(result.get("score"), (int, float)):
                    result["score"] = normalize_challenge_score(result, fb)
                    return {**fb, **result}
            except Exception:
                pass
        return fb
