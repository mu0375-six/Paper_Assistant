import json
import os
from typing import Any, Dict, Tuple

import requests


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _request(self, system_prompt: str, user_prompt: str, temperature: float = 0.3, json_mode: bool = False) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def chat_json_with_usage(self, system_prompt: str, user_prompt: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        payload = self._request(system_prompt, user_prompt, temperature=0.2, json_mode=True)
        raw = payload["choices"][0]["message"]["content"].strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Model did not return valid JSON: {raw}") from exc
        return data, self._normalize_usage(payload.get("usage", {}) or {})

    def chat_text_with_usage(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Tuple[str, Dict[str, int]]:
        payload = self._request(system_prompt, user_prompt, temperature=temperature, json_mode=False)
        raw = payload["choices"][0]["message"]["content"].strip()
        return raw, self._normalize_usage(payload.get("usage", {}) or {})

    def _normalize_usage(self, usage: Dict[str, Any]) -> Dict[str, int]:
        return {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }
