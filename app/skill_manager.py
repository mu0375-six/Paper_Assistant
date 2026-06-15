import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillManager:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = self._resolve_data_dir(data_dir)
        self.skills_path = self.data_dir / "skills.json"
        self.memory_path = self.data_dir / "memory.json"
        self._ensure_files()

    def _resolve_data_dir(self, preferred_dir: Path) -> Path:
        configured_dir = os.getenv("EVOCODER_DATA_DIR", "").strip()
        if configured_dir:
            candidate = Path(configured_dir).expanduser()
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate

        candidates = [
            preferred_dir,
            Path.home() / "Documents" / "EvoCoder-Agent" / "data",
            Path(tempfile.gettempdir()) / "EvoCoder-Agent" / "data",
        ]
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                probe = candidate / ".write_probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                return candidate
            except OSError:
                continue

        raise RuntimeError("No writable data directory is available for EvoCoder-Agent.")

    def _ensure_files(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.skills_path.exists():
            self.skills_path.write_text("[]", encoding="utf-8")
        if not self.memory_path.exists():
            self.memory_path.write_text("[]", encoding="utf-8")

    def load_skills(self) -> List[Dict[str, Any]]:
        return json.loads(self.skills_path.read_text(encoding="utf-8"))

    def load_memory(self) -> List[Dict[str, Any]]:
        return json.loads(self.memory_path.read_text(encoding="utf-8"))

    def save_skill(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        skills = self.load_skills()
        existing = next(
            (
                item
                for item in skills
                if item["name"] == skill["name"] and item.get("project_name") == skill.get("project_name")
            ),
            None,
        )
        if existing:
            existing["scenario"] = skill["scenario"]
            existing["keywords"] = skill["keywords"]
            existing["recipe"] = skill["recipe"]
            existing["learned_pattern"] = skill["learned_pattern"]
            existing["trigger"] = skill["trigger"]
            existing["project_habit"] = skill["project_habit"]
            existing["evidence_files"] = skill["evidence_files"]
            existing["updated_at"] = skill["updated_at"]
            existing["source_task"] = skill["source_task"]
            existing["times_relearned"] = existing.get("times_relearned", 0) + 1
            saved = existing
        else:
            skill["id"] = skill.get("id") or uuid.uuid4().hex[:10]
            skill["reuse_count"] = skill.get("reuse_count", 0)
            skill["times_relearned"] = 1
            skills.append(skill)
            saved = skill

        self.skills_path.write_text(json.dumps(skills, ensure_ascii=False, indent=2), encoding="utf-8")
        return saved

    def increment_reuse(self, skill_ids: List[str], timestamp: str) -> None:
        if not skill_ids:
            return
        skills = self.load_skills()
        changed = False
        for skill in skills:
            if skill.get("id") in skill_ids:
                skill["reuse_count"] = skill.get("reuse_count", 0) + 1
                skill["last_reused_at"] = timestamp
                changed = True
        if changed:
            self.skills_path.write_text(json.dumps(skills, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_memory(self, memory_item: Dict[str, Any]) -> None:
        memory = self.load_memory()
        memory.append(memory_item)
        self.memory_path.write_text(json.dumps(memory[-40:], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_project_skills(self, project_name: str) -> List[Dict[str, Any]]:
        return [item for item in self.load_skills() if item.get("project_name") == project_name]

    def get_project_memory_summary(self, project_name: str) -> Dict[str, Any]:
        project_skills = self.get_project_skills(project_name)
        project_skills.sort(key=lambda item: (item.get("reuse_count", 0), item.get("updated_at", "")), reverse=True)
        top_skills = project_skills[:5]
        return {
            "project_name": project_name,
            "skill_count": len(project_skills),
            "reused_skill_count": len([item for item in project_skills if item.get("reuse_count", 0) > 0]),
            "top_skills": top_skills,
            "known_habits": [item.get("project_habit", "") for item in top_skills if item.get("project_habit")],
        }

    def reset(self) -> None:
        self.skills_path.write_text("[]", encoding="utf-8")
        self.memory_path.write_text("[]", encoding="utf-8")
