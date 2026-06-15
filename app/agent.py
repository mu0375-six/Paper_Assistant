from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List, Optional

from .deepseek_client import DeepSeekClient
from .evaluator import build_metrics
from .planner import find_previous_similar_memory, retrieve_relevant_skills
from .project_analyzer import ProjectAnalyzer
from .skill_manager import SkillManager


TASK_SYSTEM_PROMPT = """You are an evolving coding agent for software teams.
Return JSON only using this schema:
{
  "summary": "one sentence summary",
  "steps": ["step 1", "step 2", "step 3"],
  "code_actions": ["specific code change suggestion 1", "specific code change suggestion 2"],
  "tests": ["test suggestion 1", "test suggestion 2"],
  "risks": ["risk 1", "risk 2"],
  "skill_candidate": {
    "name": "skill name",
    "scenario": "when to use it",
    "keywords": ["keyword1", "keyword2"],
    "recipe": ["action 1", "action 2", "action 3"],
    "learned_pattern": "what the agent learned from the task",
    "trigger": "when this skill should be activated again",
    "project_habit": "a project-specific convention or habit discovered in this repo"
  }
}
Keep the answer practical and grounded in the provided project files.
"""


def fallback_plan(task: str, relevant_skills: List[Dict[str, Any]], project_name: str) -> Dict[str, Any]:
    recipe = relevant_skills[0]["recipe"] if relevant_skills else [
        "Understand the request and restate the expected result.",
        "Locate the affected files and confirm the project's current pattern.",
        "Propose a minimal change plan and a verification path.",
    ]
    learned_pattern = (
        relevant_skills[0].get("learned_pattern")
        if relevant_skills
        else f"In {project_name or 'this project'}, similar tasks benefit from checking the nearest route, test, and frontend call together."
    )
    return {
        "summary": f"Create a grounded change plan for: {task}",
        "steps": recipe,
        "code_actions": [
            "Start from the most relevant file and follow the current project convention instead of inventing a new pattern.",
            "Keep the change small and call out the exact file pair that should usually be updated together.",
        ],
        "tests": [
            "Run the smallest affected test scope first.",
            "Verify one happy path and one failure path against the current project behavior.",
        ],
        "risks": [
            "The selected snippets may not contain every hidden dependency.",
            "If the project has custom conventions outside the sampled files, they should be confirmed before editing.",
        ],
        "skill_candidate": {
            "name": task[:48],
            "scenario": task,
            "keywords": task.replace(",", " ").replace(".", " ").split()[:6] or ["coding-task"],
            "recipe": recipe,
            "learned_pattern": learned_pattern,
            "trigger": f"Use when a task in {project_name or 'this repository'} touches a similar endpoint or workflow.",
            "project_habit": f"{project_name or 'This project'} tends to group route logic, test coverage, and validation changes around the same workflow.",
        },
    }


class EvolvingAgent:
    def __init__(self, skill_manager: SkillManager, llm_client: DeepSeekClient, project_analyzer: ProjectAnalyzer) -> None:
        self.skill_manager = skill_manager
        self.llm_client = llm_client
        self.project_analyzer = project_analyzer

    def run_task(
        self,
        task: str,
        context: str,
        project_path: str = "",
        uploaded_files: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        started_at = perf_counter()
        scan_started_at = perf_counter()
        project_context = self.project_analyzer.collect_context(project_path, task, context, uploaded_files)
        project_name = project_context["project_name"]

        all_skills = self.skill_manager.load_skills()
        relevant_skills = retrieve_relevant_skills(task, all_skills, project_name)
        previous_memory = find_previous_similar_memory(task, self.skill_manager.load_memory(), project_name)
        project_context = self._focus_context_with_skills(project_context, relevant_skills)
        scan_runtime_ms = round((perf_counter() - scan_started_at) * 1000, 2)

        prompt = self._build_prompt(task, context, relevant_skills, previous_memory, project_context)

        llm_usage: Dict[str, int] = {}
        llm_runtime_ms = 0.0
        mode = "reuse" if relevant_skills else "exploration"
        source = "fallback"
        if self.llm_client.is_configured():
            llm_started_at = perf_counter()
            try:
                result, llm_usage = self.llm_client.chat_json_with_usage(TASK_SYSTEM_PROMPT, prompt)
                source = "deepseek"
            except Exception as exc:
                result = fallback_plan(task, relevant_skills, project_name)
                result["warning"] = f"DeepSeek call failed, fallback plan used: {exc}"
            llm_runtime_ms = round((perf_counter() - llm_started_at) * 1000, 2)
        else:
            result = fallback_plan(task, relevant_skills, project_name)
            result["warning"] = "DEEPSEEK_API_KEY is not configured, fallback plan used."

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_skill = {
            "name": result["skill_candidate"]["name"],
            "project_name": project_name,
            "scenario": result["skill_candidate"]["scenario"],
            "keywords": result["skill_candidate"]["keywords"],
            "recipe": result["skill_candidate"]["recipe"],
            "learned_pattern": result["skill_candidate"]["learned_pattern"],
            "trigger": result["skill_candidate"]["trigger"],
            "project_habit": result["skill_candidate"]["project_habit"],
            "evidence_files": [item["path"] for item in project_context["selected_files"][:4]],
            "source_task": task,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        saved_skill = self.skill_manager.save_skill(new_skill)
        self.skill_manager.increment_reuse([item["id"] for item in relevant_skills if item.get("id")], timestamp)

        total_runtime_ms = round((perf_counter() - started_at) * 1000, 2)
        metrics = build_metrics(
            task=task,
            reused_skill_count=len(relevant_skills),
            steps=result["steps"],
            prompt_text=prompt,
            project_chars=project_context["project_chars"],
            llm_usage=llm_usage,
            total_runtime_ms=total_runtime_ms,
            scan_runtime_ms=scan_runtime_ms,
            llm_runtime_ms=llm_runtime_ms,
            selected_file_count=len(project_context["selected_files"]),
            scanned_file_count=project_context["scanned_file_count"],
        )

        comparison = self._build_comparison(previous_memory, metrics, project_context, relevant_skills)
        project_memory = self.skill_manager.get_project_memory_summary(project_name)
        evolution_story = self._build_evolution_story(mode, saved_skill, relevant_skills, project_memory, comparison)

        memory_item = {
            "task": task,
            "summary": result["summary"],
            "project_name": project_name,
            "mode": mode,
            "reused_skills": [item["name"] for item in relevant_skills],
            "created_skill": saved_skill["name"],
            "timestamp": timestamp,
            "metrics": metrics,
            "comparison": comparison,
        }
        self.skill_manager.append_memory(memory_item)

        return {
            "task": task,
            "context": context,
            "source": source,
            "mode": mode,
            "summary": result["summary"],
            "steps": result["steps"],
            "code_actions": result["code_actions"],
            "tests": result["tests"],
            "risks": result.get("risks", []),
            "warning": result.get("warning", ""),
            "reused_skills": relevant_skills,
            "created_skill": saved_skill,
            "project_analysis": {
                "project_name": project_name,
                "summary": project_context["summary"],
                "selected_files": project_context["selected_files"],
                "scanned_file_count": project_context["scanned_file_count"],
            },
            "metrics": metrics,
            "comparison": comparison,
            "project_memory": project_memory,
            "evolution_story": evolution_story,
            "timeline": self._build_timeline(mode, relevant_skills, saved_skill, project_context, comparison),
        }

    def preview_project(self, project_path: str) -> Dict[str, Any]:
        return self.project_analyzer.preview_project(project_path)

    def preview_snapshot(self, uploaded_files: List[Dict[str, str]]) -> Dict[str, Any]:
        return self.project_analyzer.preview_snapshot(uploaded_files)

    def _focus_context_with_skills(self, project_context: Dict[str, Any], relevant_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not relevant_skills:
            return project_context

        evidence_paths = []
        for skill in relevant_skills:
            evidence_paths.extend(skill.get("evidence_files", []))

        if not evidence_paths:
            return project_context

        selected = project_context["selected_files"]
        prioritized = [item for item in selected if item["path"] in evidence_paths]
        remaining = [item for item in selected if item["path"] not in evidence_paths]
        focused = (prioritized + remaining)[:4]
        project_context["selected_files"] = focused
        project_context["project_chars"] = sum(len(item["snippet"]) for item in focused)
        project_context["summary"] += " Reused skills helped narrow attention to previously relevant files."
        return project_context

    def _build_prompt(
        self,
        task: str,
        context: str,
        relevant_skills: List[Dict[str, Any]],
        previous_memory: Optional[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> str:
        skill_block = "No reusable skills found."
        if relevant_skills:
            skill_block = "\n".join(
                (
                    f"- Skill: {item['name']}\n"
                    f"  Learned pattern: {item.get('learned_pattern', '')}\n"
                    f"  Trigger: {item.get('trigger', '')}\n"
                    f"  Recipe: {' -> '.join(item['recipe'])}\n"
                    f"  Evidence files: {', '.join(item.get('evidence_files', []))}"
                )
                for item in relevant_skills
            )

        memory_block = "No prior similar run."
        if previous_memory:
            memory_block = (
                f"Previous similar task: {previous_memory.get('task')}\n"
                f"Mode: {previous_memory.get('mode')}\n"
                f"Created skill: {previous_memory.get('created_skill')}\n"
                f"Reused skills then: {', '.join(previous_memory.get('reused_skills', [])) or 'none'}"
            )

        file_block = "\n\n".join(
            f"[File] {item['path']}\n[Reason] {item['reason']}\n[Snippet]\n{item['snippet']}"
            for item in project_context["selected_files"]
        ) or "No project files were selected."

        return (
            f"Task:\n{task}\n\n"
            f"Extra context:\n{context or 'None'}\n\n"
            f"Reusable project skills:\n{skill_block}\n\n"
            f"Prior similar execution:\n{memory_block}\n\n"
            f"Project summary:\n{project_context['summary']}\n\n"
            f"Relevant project files:\n{file_block}\n\n"
            "Produce concrete change advice and explicitly reflect what this run teaches the agent about this project."
        )

    def _build_comparison(
        self,
        previous_memory: Optional[Dict[str, Any]],
        metrics: Dict[str, Any],
        project_context: Dict[str, Any],
        relevant_skills: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        previous_metrics = previous_memory.get("metrics", {}) if previous_memory else {}
        return {
            "has_previous": bool(previous_memory),
            "previous_task": previous_memory.get("task") if previous_memory else "",
            "current_selected_files": len(project_context["selected_files"]),
            "previous_selected_files": previous_metrics.get("selected_file_count", 0),
            "current_step_count": metrics["step_count"],
            "previous_step_count": previous_metrics.get("step_count", 0),
            "current_tokens": metrics["total_tokens"],
            "previous_tokens": previous_metrics.get("total_tokens", 0),
            "current_runtime_ms": metrics["total_runtime_ms"],
            "previous_runtime_ms": previous_metrics.get("total_runtime_ms", 0),
            "guided_by_skill": bool(relevant_skills),
            "reused_skill_names": [item["name"] for item in relevant_skills],
        }

    def _build_evolution_story(
        self,
        mode: str,
        new_skill: Dict[str, Any],
        reused_skills: List[Dict[str, Any]],
        project_memory: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        if mode == "exploration":
            headline = "首次探索这个项目中的这类任务"
            proof = "这次的重点不是节省，而是把项目里的处理套路沉淀成下次可复用的技能。"
        else:
            headline = "已进入项目内复用阶段"
            proof = "这次不是从头分析，而是先调用项目内已有技能，再补充新的观察。"

        return {
            "headline": headline,
            "proof": proof,
            "new_capability": new_skill.get("learned_pattern", ""),
            "project_habit": new_skill.get("project_habit", ""),
            "reuse_signal": reused_skills[0]["name"] if reused_skills else "暂无复用技能",
            "project_skill_count": project_memory["skill_count"],
            "comparison_note": self._comparison_note(comparison),
        }

    def _comparison_note(self, comparison: Dict[str, Any]) -> str:
        if not comparison["has_previous"]:
            return "当前还没有可对照的上一条相似任务，这次运行会作为后续复用的基线。"
        if comparison["guided_by_skill"]:
            return (
                f"与上一条相似任务相比，这次直接命中了 {len(comparison['reused_skill_names'])} 条技能，"
                "说明 agent 已经开始沿用项目内经验。"
            )
        return "虽然找到了上一条相似任务，但这次还没有命中可复用技能，仍处在继续积累阶段。"

    def _build_timeline(
        self,
        mode: str,
        reused_skills: List[Dict[str, Any]],
        new_skill: Dict[str, Any],
        project_context: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        return [
            {
                "title": "读取项目",
                "detail": f"本次扫描了 {project_context['scanned_file_count']} 个候选文件，并聚焦到 {len(project_context['selected_files'])} 个关键文件。",
            },
            {
                "title": "判断执行模式",
                "detail": (
                    f"本次属于{'复用' if mode == 'reuse' else '探索'}模式。"
                    + (f" 优先调用了：{', '.join(item['name'] for item in reused_skills)}。" if reused_skills else " 还没有历史技能可用。")
                ),
            },
            {
                "title": "生成项目经验",
                "detail": f"本次沉淀的新技能是“{new_skill['name']}”，它总结的是：{new_skill.get('learned_pattern', '')}",
            },
            {
                "title": "进入下次复用",
                "detail": self._comparison_note(comparison),
            },
        ]
