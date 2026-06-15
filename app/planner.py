from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def retrieve_relevant_skills(
    task: str,
    skills: List[Dict[str, Any]],
    project_name: str = "",
) -> List[Dict[str, Any]]:
    ranked = []
    for skill in skills:
        score = max(
            similarity(task, skill.get("name", "")),
            similarity(task, skill.get("scenario", "")),
            similarity(task, " ".join(skill.get("keywords", []))),
        )
        if project_name and skill.get("project_name") == project_name:
            score += 0.12
        if score >= 0.22:
            ranked.append((score, skill))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:3]]


def find_previous_similar_memory(
    task: str,
    memory_items: List[Dict[str, Any]],
    project_name: str = "",
) -> Optional[Dict[str, Any]]:
    ranked = []
    for item in memory_items:
        if project_name and item.get("project_name") != project_name:
            continue
        score = similarity(task, item.get("task", ""))
        if score >= 0.22:
            ranked.append((score, item))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else None
