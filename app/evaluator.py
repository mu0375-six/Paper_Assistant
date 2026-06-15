from typing import Dict, List


def estimate_tokens_from_text(text: str) -> int:
    return max(1, len(text) // 4)


def build_metrics(
    task: str,
    reused_skill_count: int,
    steps: List[str],
    prompt_text: str,
    project_chars: int,
    llm_usage: Dict[str, int],
    total_runtime_ms: float,
    scan_runtime_ms: float,
    llm_runtime_ms: float,
    selected_file_count: int,
    scanned_file_count: int,
) -> Dict[str, float]:
    estimated_prompt_tokens = estimate_tokens_from_text(prompt_text)
    estimated_completion_tokens = max(120, len(" ".join(steps)) * 2)

    prompt_tokens = llm_usage.get("prompt_tokens") or estimated_prompt_tokens
    completion_tokens = llm_usage.get("completion_tokens") or estimated_completion_tokens
    total_tokens = llm_usage.get("total_tokens") or (prompt_tokens + completion_tokens)

    saved_tokens = reused_skill_count * 240
    baseline_tokens_without_reuse = total_tokens + saved_tokens
    next_run_saved_tokens_estimate = max(180, len(steps) * 70) if reused_skill_count == 0 else saved_tokens

    baseline_runtime_ms = round(total_runtime_ms + reused_skill_count * 850, 2)
    next_run_saved_runtime_ms = max(600.0, len(steps) * 220.0) if reused_skill_count == 0 else max(0.0, round(baseline_runtime_ms - total_runtime_ms, 2))
    runtime_saved_ms = max(0.0, round(baseline_runtime_ms - total_runtime_ms, 2))

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "baseline_tokens_without_reuse": baseline_tokens_without_reuse,
        "saved_tokens_estimate": saved_tokens,
        "next_run_saved_tokens_estimate": next_run_saved_tokens_estimate,
        "total_runtime_ms": total_runtime_ms,
        "scan_runtime_ms": scan_runtime_ms,
        "llm_runtime_ms": llm_runtime_ms,
        "baseline_runtime_ms": baseline_runtime_ms,
        "runtime_saved_ms": runtime_saved_ms,
        "next_run_saved_runtime_ms": next_run_saved_runtime_ms,
        "selected_file_count": selected_file_count,
        "scanned_file_count": scanned_file_count,
        "project_chars": project_chars,
        "step_count": len(steps),
        "reused_skill_count": reused_skill_count,
    }
