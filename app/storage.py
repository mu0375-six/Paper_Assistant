import json
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class JsonStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = self._resolve_base_dir(base_dir)
        self.papers_path = self.base_dir / "papers.json"
        self.notes_path = self.base_dir / "notes.json"
        self.search_history_path = self.base_dir / "search_history.json"
        self.plans_path = self.base_dir / "plans.json"
        self.drafts_path = self.base_dir / "writing_drafts.json"
        self.assistant_messages_path = self.base_dir / "assistant_messages.json"
        self.challenge_runs_path = self.base_dir / "challenge_runs.json"
        self.downloads_dir = self.base_dir / "downloads"
        self._ensure_files()

    def _resolve_base_dir(self, preferred: Path) -> Path:
        candidates = [
            preferred,
            Path.home() / "Documents" / "ScholarFlow" / "data",
            Path(tempfile.gettempdir()) / "ScholarFlow" / "data",
        ]
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                probe = candidate / ".probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                return candidate
            except OSError:
                continue
        raise RuntimeError("No writable data directory available.")

    def _ensure_files(self) -> None:
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        for path in [
            self.papers_path,
            self.notes_path,
            self.search_history_path,
            self.plans_path,
            self.drafts_path,
            self.assistant_messages_path,
            self.challenge_runs_path,
        ]:
            if not path.exists():
                path.write_text("[]", encoding="utf-8")

    def _read(self, path: Path) -> List[Dict[str, Any]]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, payload: List[Dict[str, Any]]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_record(self, path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
        records = self._read(path)
        if not payload.get("id"):
            payload["id"] = uuid.uuid4().hex[:12]
            records.append(payload)
        else:
            for index, item in enumerate(records):
                if item["id"] == payload["id"]:
                    records[index] = payload
                    break
            else:
                records.append(payload)
        self._write(path, records)
        return payload

    def list_papers(self) -> List[Dict[str, Any]]:
        return self._read(self.papers_path)

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        return next((item for item in self.list_papers() if item["id"] == paper_id), None)

    def save_paper(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_record(self.papers_path, payload)

    def list_notes(self) -> List[Dict[str, Any]]:
        return self._read(self.notes_path)

    def list_notes_for_paper(self, paper_id: str) -> List[Dict[str, Any]]:
        return [item for item in self.list_notes() if item["paper_id"] == paper_id]

    def save_note(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_record(self.notes_path, payload)

    def list_search_history(self) -> List[Dict[str, Any]]:
        return self._read(self.search_history_path)

    def save_search_history(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_record(self.search_history_path, payload)

    def list_plans(self) -> List[Dict[str, Any]]:
        return self._read(self.plans_path)

    def save_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_record(self.plans_path, payload)

    def list_writing_drafts(self) -> List[Dict[str, Any]]:
        return self._read(self.drafts_path)

    def save_writing_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_record(self.drafts_path, payload)

    def list_assistant_messages(self) -> List[Dict[str, Any]]:
        return self._read(self.assistant_messages_path)

    def list_assistant_messages_for_paper(self, paper_id: str) -> List[Dict[str, Any]]:
        return [item for item in self.list_assistant_messages() if item["paper_id"] == paper_id]

    def save_assistant_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_record(self.assistant_messages_path, payload)

    def list_challenge_runs(self) -> List[Dict[str, Any]]:
        return self._read(self.challenge_runs_path)

    def list_challenge_runs_for_paper(self, paper_id: str) -> List[Dict[str, Any]]:
        return [item for item in self.list_challenge_runs() if item["paper_id"] == paper_id]

    def save_challenge_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._save_record(self.challenge_runs_path, payload)

    def stats(self) -> Dict[str, Any]:
        papers = self.list_papers()
        notes = self.list_notes()
        history = self.list_search_history()
        analyzed = len([item for item in papers if item.get("analysis")])
        return {
            "paper_count": len(papers),
            "analyzed_count": analyzed,
            "note_count": len(notes),
            "search_count": len(history),
            "plan_count": len(self.list_plans()),
            "draft_count": len(self.list_writing_drafts()),
            "storage_dir": str(self.base_dir),
        }
