import os
import re
from pathlib import Path
from typing import Dict, List, Optional


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".next",
    ".idea",
    ".vscode",
}

ALLOWED_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".cs",
    ".json",
    ".md",
    ".yml",
    ".yaml",
    ".html",
    ".css",
    ".sql",
    ".sh",
}


class ProjectAnalyzer:
    def preview_snapshot(self, uploaded_files: List[Dict[str, str]]) -> Dict[str, object]:
        if not uploaded_files:
            return {
                "valid": False,
                "message": "No files were selected from the folder.",
                "project_name": "",
                "project_path": "",
                "file_count": 0,
                "sample_files": [],
            }

        root_name = uploaded_files[0].get("root_name", "") or "Selected Folder"
        sample_files = [item["path"] for item in uploaded_files[:8]]
        return {
            "valid": True,
            "message": f"Loaded {len(uploaded_files)} files from the selected folder.",
            "project_name": root_name,
            "project_path": "[browser folder selection]",
            "file_count": len(uploaded_files),
            "sample_files": sample_files,
        }

    def preview_project(self, project_path: str) -> Dict[str, object]:
        path = Path(project_path).expanduser()
        if not project_path.strip():
            return {
                "valid": False,
                "message": "No local project path provided.",
                "project_name": "",
                "project_path": "",
                "file_count": 0,
                "sample_files": [],
            }

        resolved = path.resolve()

        if not resolved.exists() or not resolved.is_dir():
            return {
                "valid": False,
                "message": "The path does not exist or is not a directory.",
                "project_name": resolved.name or str(resolved),
                "project_path": str(resolved),
                "file_count": 0,
                "sample_files": [],
            }

        files = self._collect_files(resolved)
        return {
            "valid": True,
            "message": f"Scanned {len(files)} candidate files.",
            "project_name": resolved.name or str(resolved),
            "project_path": str(resolved),
            "file_count": len(files),
            "sample_files": [str(item.relative_to(resolved)) for item in files[:8]],
        }

    def collect_context(
        self,
        project_path: str,
        task: str,
        extra_context: str,
        uploaded_files: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, object]:
        if uploaded_files:
            selected_files = self._select_relevant_uploaded_files(uploaded_files, task, extra_context)
            project_chars = sum(len(item["snippet"]) for item in selected_files)
            root_name = uploaded_files[0].get("root_name", "") or "Selected Folder"
            return {
                "project_name": root_name,
                "project_path": "[browser folder selection]",
                "summary": (
                    f"Browser-selected folder '{root_name}' loaded with "
                    f"{len(uploaded_files)} files. Selected {len(selected_files)} relevant files "
                    "for this task."
                ),
                "selected_files": selected_files,
                "scanned_file_count": len(uploaded_files),
                "project_chars": project_chars,
            }

        preview = self.preview_project(project_path)
        if not preview["valid"]:
            return {
                "project_name": preview["project_name"] or "No project selected",
                "project_path": preview["project_path"],
                "summary": preview["message"],
                "selected_files": [],
                "scanned_file_count": 0,
                "project_chars": 0,
            }

        root = Path(preview["project_path"])
        files = self._collect_files(root)
        selected_files = self._select_relevant_files(root, files, task, extra_context)
        project_chars = sum(len(item["snippet"]) for item in selected_files)

        return {
            "project_name": preview["project_name"],
            "project_path": preview["project_path"],
            "summary": (
                f"Local project '{preview['project_name']}' scanned with "
                f"{len(files)} candidate files. Selected {len(selected_files)} relevant files "
                "for this task."
            ),
            "selected_files": selected_files,
            "scanned_file_count": len(files),
            "project_chars": project_chars,
        }

    def _select_relevant_uploaded_files(
        self,
        uploaded_files: List[Dict[str, str]],
        task: str,
        extra_context: str,
    ) -> List[Dict[str, object]]:
        keywords = self._extract_keywords(f"{task} {extra_context}")
        ranked = []
        for item in uploaded_files:
            rel_path = item["path"]
            rel_lower = rel_path.lower()
            snippet = item["content"][:3200]
            score = 0
            for keyword in keywords:
                if keyword in rel_lower:
                    score += 6
                if keyword in snippet.lower():
                    score += 3
            score += max(0, 3 - rel_path.count("/"))
            ranked.append((score, rel_path, snippet))

        ranked.sort(key=lambda entry: entry[0], reverse=True)
        selected = []
        for score, rel_path, snippet in ranked[:6]:
            matching_keywords = [keyword for keyword in keywords if keyword in rel_path.lower() or keyword in snippet.lower()]
            selected.append(
                {
                    "path": rel_path,
                    "score": score,
                    "reason": (
                        f"Matched keywords: {', '.join(matching_keywords[:4])}"
                        if matching_keywords
                        else "Relevant by filename and nearby content."
                    ),
                    "snippet": snippet,
                }
            )
        return selected

    def _collect_files(self, root: Path) -> List[Path]:
        files: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS]
            current_dir = Path(dirpath)
            for filename in filenames:
                path = current_dir / filename
                if path.suffix.lower() not in ALLOWED_SUFFIXES:
                    continue
                if path.stat().st_size > 300_000:
                    continue
                files.append(path)
                if len(files) >= 160:
                    return files
        return files

    def _select_relevant_files(
        self,
        root: Path,
        files: List[Path],
        task: str,
        extra_context: str,
    ) -> List[Dict[str, object]]:
        keywords = self._extract_keywords(f"{task} {extra_context}")
        ranked = []
        for path in files:
            rel_path = str(path.relative_to(root))
            score = 0
            rel_lower = rel_path.lower()
            for keyword in keywords:
                if keyword in rel_lower:
                    score += 6
            snippet = self._read_snippet(path)
            snippet_lower = snippet.lower()
            for keyword in keywords:
                if keyword in snippet_lower:
                    score += 3
            score += max(0, 3 - rel_path.count("\\"))
            ranked.append((score, path, snippet))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = []
        for score, path, snippet in ranked[:6]:
            reason_parts = []
            rel_path = str(path.relative_to(root))
            rel_lower = rel_path.lower()
            matching_keywords = [keyword for keyword in keywords if keyword in rel_lower or keyword in snippet.lower()]
            if matching_keywords:
                reason_parts.append(f"Matched keywords: {', '.join(matching_keywords[:4])}")
            if score <= 3:
                reason_parts.append("Included as a likely entry or nearby file.")
            selected.append(
                {
                    "path": rel_path,
                    "score": score,
                    "reason": " ".join(reason_parts) or "Relevant by filename and local structure.",
                    "snippet": snippet,
                }
            )
        return selected

    def _extract_keywords(self, text: str) -> List[str]:
        tokens = re.findall(r"[a-zA-Z_]{3,}|[0-9]{3,}", text.lower())
        stop_words = {
            "with",
            "from",
            "into",
            "that",
            "this",
            "your",
            "have",
            "login",
            "user",
            "make",
            "task",
            "code",
            "test",
        }
        filtered = []
        for token in tokens:
            if token in stop_words:
                continue
            if token not in filtered:
                filtered.append(token)
        return filtered[:10]

    def _read_snippet(self, path: Path) -> str:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                text = path.read_text(encoding="latin-1", errors="ignore")

        lines = text.splitlines()
        head = "\n".join(lines[:80])
        return head[:3200]
