"""论文管理服务 Mixin。

包含论文 CRUD、PDF 处理、AI 精读、翻译、句子检索、AI 问答、笔记等逻辑。
依赖 self.store 和 self.llm_client（由 ScholarService 设置）。
"""

import io
import re
from pathlib import Path
from typing import Any, Dict, List

import requests

from .constants import (
    ANALYSIS_PROMPT,
    ASSISTANT_PROMPT,
    CHALLENGE_STAGES,
    TRANSLATION_PROMPT,
)
from .helpers import (
    build_catalog_content,
    ensure_reader_content,
    fallback_analysis,
    fallback_assistant,
    guess_abstract,
    guess_authors,
    guess_source,
    guess_title,
    guess_year,
    now,
    safe_filename,
    split_sentences,
    tokenize,
)


class PaperMixin:
    """论文管理相关的方法。

    需要 self.store (JsonStore) 和 self.llm_client (DeepSeekClient)。
    """

    def dashboard(self) -> Dict[str, Any]:
        papers = [ensure_reader_content(dict(item)) for item in self.store.list_papers()]
        notes = self.store.list_notes()
        search_history = self.store.list_search_history()
        plans = self.store.list_plans()
        drafts = self.store.list_writing_drafts()
        assistant_messages = self.store.list_assistant_messages()
        latest = sorted(papers, key=lambda item: item["updated_at"], reverse=True)[:5]
        return {
            **self.store.stats(),
            "latest_papers": latest,
            "papers": sorted(papers, key=lambda item: item["updated_at"], reverse=True),
            "notes": sorted(notes, key=lambda item: item["updated_at"], reverse=True),
            "search_history": sorted(search_history, key=lambda item: item["created_at"], reverse=True)[:12],
            "plans": sorted(plans, key=lambda item: item["created_at"], reverse=True),
            "writing_drafts": sorted(drafts, key=lambda item: item["created_at"], reverse=True),
            "assistant_messages": sorted(assistant_messages, key=lambda item: item["created_at"], reverse=True),
        }

    def get_paper(self, paper_id: str) -> Dict[str, Any]:
        paper = self.store.get_paper(paper_id)
        if not paper:
            raise ValueError("Paper not found.")
        return ensure_reader_content(dict(paper))

    def extract_pdf(self, file_storage) -> Dict[str, Any]:
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError("pypdf is not installed. Please install it before using PDF upload.") from exc

        raw_bytes = file_storage.read()
        filename = file_storage.filename or "uploaded.pdf"
        safe_stem = safe_filename(Path(filename).stem or "uploaded")
        saved_pdf = self.store.downloads_dir / f"{safe_stem}.pdf"
        saved_pdf.write_bytes(raw_bytes)

        reader = PdfReader(io.BytesIO(raw_bytes))
        metadata = reader.metadata or {}
        pages_text = []
        for page in reader.pages:
            try:
                pages_text.append((page.extract_text() or "").strip())
            except Exception:
                pages_text.append("")

        full_text = "\n\n".join(part for part in pages_text if part).strip()
        first_page_text = pages_text[0] if pages_text else ""

        title = guess_title(metadata, first_page_text, file_storage.filename or "")
        authors = guess_authors(metadata, first_page_text)
        year = guess_year(metadata, full_text)
        abstract = guess_abstract(full_text)
        source = guess_source(filename, first_page_text)
        figures = self._extract_pdf_images(reader, safe_stem)

        return {
            "title": title,
            "authors": authors,
            "year": year,
            "source": source,
            "abstract": abstract,
            "content": full_text,
            "pages": pages_text,
            "figures": figures,
            "page_count": len(reader.pages),
            "filename": filename,
            "downloaded_pdf_url": f"/downloads/{saved_pdf.name}",
            "needs_review": True,
        }

    def import_pdf(self, file_storage) -> Dict[str, Any]:
        extracted = self.extract_pdf(file_storage)
        paper = self.create_paper(extracted)
        paper["import_meta"] = {
            "filename": extracted["filename"],
            "page_count": extracted["page_count"],
            "needs_review": extracted["needs_review"],
        }
        return paper

    def create_paper(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        _now = now()
        existing = self.store.get_paper(payload.get("id", "")) if payload.get("id") else None
        paper = {
            "id": payload.get("id", ""),
            "title": (payload.get("title") or "").strip(),
            "authors": (payload.get("authors") or "").strip(),
            "year": (payload.get("year") or "").strip(),
            "source": (payload.get("source") or "").strip(),
            "abstract": (payload.get("abstract") or "").strip(),
            "content": (payload.get("content") or "").strip(),
            "pages": payload.get("pages") or (existing or {}).get("pages", []),
            "figures": payload.get("figures") or (existing or {}).get("figures", []),
            "pdf_url": (payload.get("pdf_url") or (existing or {}).get("pdf_url") or "").strip(),
            "text_url": (payload.get("text_url") or (existing or {}).get("text_url") or "").strip(),
            "downloaded_pdf_url": payload.get("downloaded_pdf_url") or (existing or {}).get("downloaded_pdf_url", ""),
            "analysis": payload.get("analysis") or (existing or {}).get("analysis", {}),
            "translations": payload.get("translations") or (existing or {}).get("translations", {}),
            "tutorial_sample": bool(payload.get("tutorial_sample") or (existing or {}).get("tutorial_sample", False)),
            "created_at": payload.get("created_at") or (existing or {}).get("created_at") or _now,
            "updated_at": _now,
        }
        return self.store.save_paper(paper)

    def ensure_sample_paper(self) -> Dict[str, Any]:
        sample_id = "sample-paper-reading-guide"
        existing = self.store.get_paper(sample_id)
        if existing:
            return existing

        pages = [
            (
                "标题：AI 辅助学术阅读工作流：从论文筛选到课堂汇报\n"
                "作者：ScholarFlow Tutorial Team\n"
                "摘要：本文提出一个面向本科生和研究生的 AI 辅助论文阅读工作流。"
                "该工作流并不让 AI 直接替代阅读，而是把论文阅读拆解为研究问题识别、方法流程理解、"
                "图表证据判断、局限分析和汇报表达五个训练环节。"
                "关键词：学术阅读；AI 辅助学习；论文精读；课堂汇报"
            ),
            (
                "1 引言\n"
                "许多学生在第一次阅读论文时会直接从头读到尾，却很难判断论文真正要解决什么问题。"
                "更有效的方式是先阅读标题、摘要和引言末尾，找出作者指出的研究空白。"
                "本文的研究问题是：如何让 AI 工具帮助学习者形成可复用的论文阅读方法，而不是只生成一段摘要。"
                "本文贡献包括：第一，提出六步阅读路线；第二，设计五关闯关问答；第三，把纠错结果转化为课堂汇报材料。"
            ),
            (
                "2 方法\n"
                "输入数据包括论文标题、摘要、正文片段、用户选区和阅读笔记。"
                "处理步骤包括：先抽取关键词和研究问题，再生成阅读问题，随后根据学生回答进行纠错评分，"
                "最后把通过训练的内容整理成课堂汇报。输出结果包括结构化摘要、错题反馈、阅读笔记和汇报提纲。"
            ),
            (
                "3 结果与讨论\n"
                "示例使用中，学生先通过阅读台查看论文，再点击 AI 精读获取上下文，随后进入闯关区回答五类问题。"
                "当答案过于笼统时，系统会指出缺失的证据，并提示回到摘要、引言、方法或图表附近查找依据。"
                "局限在于：AI 反馈仍需要用户结合原文判断；如果上传的 PDF 质量较差，文本抽取可能不完整。"
                "4 结论\n"
                "AI 辅助阅读最有价值的地方不是替学生完成阅读，而是把阅读过程变成可练习、可纠错、可汇报的学习闭环。"
            ),
        ]
        return self.create_paper(
            {
                "id": sample_id,
                "title": "示例论文：AI 辅助学术阅读工作流",
                "authors": "ScholarFlow Tutorial Team",
                "year": "2026",
                "source": "内置教程示例",
                "abstract": pages[0],
                "content": "\n\n".join(pages),
                "pages": pages,
                "tutorial_sample": True,
                "analysis": {
                    "summary": "这是一篇用于教学演示的示例论文，展示如何从研究问题、方法流程、证据判断、局限分析到课堂汇报完成一次完整精读。",
                    "keywords": ["学术阅读", "AI 辅助学习", "论文精读", "课堂汇报"],
                    "research_problem": "如何让 AI 工具帮助学习者形成可复用的论文阅读方法，而不是只生成摘要。",
                    "method": "输入论文文本和用户选区，经过关键词抽取、阅读问题生成、闯关纠错评分和汇报整理，输出笔记与课堂汇报材料。",
                    "findings": ["六步阅读路线能降低新手进入论文的门槛。", "闯关纠错可以暴露学生对方法、证据和局限的理解缺口。"],
                    "limitations": ["示例论文不是正式发表论文。", "AI 反馈仍需要用户回到原文核对。"],
                    "reading_questions": ["这篇论文想解决的新手阅读痛点是什么？", "六步阅读路线分别对应哪些学习动作？", "AI 闯关评分如何帮助形成课堂汇报？"],
                },
            }
        )

    def analyze_paper(self, paper_id: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        user_prompt = (
            f"Title: {paper['title']}\n"
            f"Authors: {paper['authors']}\n"
            f"Year: {paper['year']}\n"
            f"Abstract: {paper['abstract']}\n\n"
            f"Content:\n{paper['content'][:12000]}"
        )
        if self.llm_client.is_configured():
            try:
                analysis, _usage = self.llm_client.chat_json_with_usage(ANALYSIS_PROMPT, user_prompt)
            except Exception:
                analysis = fallback_analysis(paper)
        else:
            analysis = fallback_analysis(paper)

        paper["analysis"] = analysis
        paper["updated_at"] = now()
        return self.store.save_paper(paper)

    def translate_paper(self, paper_id: str, target_language: str, scope: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        scope_text = {
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "content": paper.get("content", ""),
        }.get(scope, paper.get("abstract") or paper.get("content", ""))
        translated = self._translate_text(scope_text[:8000], target_language)
        key = f"{scope}_{target_language}"
        paper.setdefault("translations", {})[key] = translated["translated_text"]
        paper["updated_at"] = now()
        self.store.save_paper(paper)
        return {
            "paper_id": paper_id,
            "scope": scope,
            "target_language": target_language,
            "translated_text": translated["translated_text"],
        }

    def sentence_search(self, paper_id: str, query: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        sentences = split_sentences(paper.get("content", ""))
        query_tokens = tokenize(query)
        matches = []
        for index, sentence in enumerate(sentences):
            haystack = sentence.lower()
            score = sum(2 for token in query_tokens if token.lower() in haystack)
            if query.lower() in haystack:
                score += 4
            if score > 0:
                matches.append({"index": index + 1, "sentence": sentence, "score": score})
        matches.sort(key=lambda item: item["score"], reverse=True)
        return {"paper_id": paper_id, "query": query, "matches": matches[:10]}

    def assistant_chat(self, paper_id: str, message: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        history = self.store.list_assistant_messages_for_paper(paper_id)[-6:]
        history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history)
        user_prompt = (
            f"Paper title: {paper['title']}\n"
            f"Abstract: {paper.get('abstract', '')}\n"
            f"Analysis: {paper.get('analysis', {})}\n"
            f"Content excerpt:\n{paper.get('content', '')[:8000]}\n\n"
            f"Chat history:\n{history_text}\n\n"
            f"User question: {message}"
        )
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(ASSISTANT_PROMPT, user_prompt)
                answer = result.get("answer", "").strip()
                followups = result.get("followups", [])
            except Exception:
                answer, followups = fallback_assistant(paper, message)
        else:
            answer, followups = fallback_assistant(paper, message)

        user_record = self.store.save_assistant_message(
            {"paper_id": paper_id, "role": "user", "content": message, "created_at": now()}
        )
        assistant_record = self.store.save_assistant_message(
            {"paper_id": paper_id, "role": "assistant", "content": answer, "followups": followups, "created_at": now()}
        )
        return {"paper_id": paper_id, "messages": [user_record, assistant_record], "followups": followups}

    def save_note(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        _now = now()
        note = {
            "id": payload.get("id", ""),
            "paper_id": payload["paper_id"],
            "title": (payload.get("title") or "").strip() or "阅读笔记",
            "content": (payload.get("content") or "").strip(),
            "kind": (payload.get("kind") or "manual").strip(),
            "source_text": (payload.get("source_text") or "").strip(),
            "page_label": (payload.get("page_label") or "").strip(),
            "anchor_text": (payload.get("anchor_text") or "").strip(),
            "ai_prompt": (payload.get("ai_prompt") or "").strip(),
            "assistant_message_id": (payload.get("assistant_message_id") or "").strip(),
            "created_at": payload.get("created_at") or _now,
            "updated_at": _now,
        }
        return self.store.save_note(note)

    # ── 内部方法 ───────────────────────────────────────────

    def _extract_pdf_from_url(self, pdf_url: str, title: str) -> Dict[str, Any]:
        response = requests.get(pdf_url, timeout=120)
        response.raise_for_status()
        raw_bytes = response.content
        filename = safe_filename(title or "paper") + ".pdf"
        target = self.store.downloads_dir / filename
        if not target.exists():
            target.write_bytes(raw_bytes)

        try:
            from pypdf import PdfReader
        except Exception:
            return {
                "content": build_catalog_content({"title": title}),
                "pages": [],
                "downloaded_pdf_url": f"/downloads/{filename}",
            }

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        figures = self._extract_pdf_images(reader, safe_filename(title or "paper"))
        for page in reader.pages:
            try:
                page_text = (page.extract_text() or "").strip()
            except Exception:
                page_text = ""
            if page_text:
                pages.append(page_text)

        content = "\n\n".join(pages).strip()
        return {
            "content": content or build_catalog_content({"title": title}),
            "pages": pages,
            "figures": figures,
            "downloaded_pdf_url": f"/downloads/{filename}",
        }

    def _extract_pdf_images(self, reader, stem: str, max_images: int = 8) -> List[Dict[str, Any]]:
        figures: List[Dict[str, Any]] = []
        image_dir = self.store.downloads_dir / "figures"
        image_dir.mkdir(parents=True, exist_ok=True)
        _safe_stem = safe_filename(stem or "paper")

        for page_index, page in enumerate(reader.pages, start=1):
            try:
                page_images = getattr(page, "images", []) or []
            except Exception:
                continue
            try:
                for image_index, image in enumerate(page_images, start=1):
                    try:
                        if len(figures) >= max_images:
                            return figures
                        data = getattr(image, "data", b"") or b""
                        if len(data) < 4096:
                            continue
                        original_name = getattr(image, "name", "") or f"figure-{image_index}.png"
                        suffix = Path(original_name).suffix.lower() or ".png"
                        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
                            suffix = ".png"
                        img_filename = f"{_safe_stem}-p{page_index}-fig{image_index}{suffix}"
                        target = image_dir / img_filename
                        target.write_bytes(data)
                        figures.append({
                            "url": f"/downloads/figures/{img_filename}",
                            "caption": f"Figure {len(figures) + 1}. Extracted from page {page_index}",
                            "page": page_index,
                        })
                    except Exception:
                        continue
            except Exception:
                continue
        return figures

    def _translate_text(self, text: str, target_language: str) -> Dict[str, str]:
        if not text.strip():
            return {"translated_text": "", "detected_language": "", "target_language": target_language}

        prompt = f"Target language: {target_language}\n\nText:\n{text}"
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(TRANSLATION_PROMPT, prompt)
                return {
                    "translated_text": result.get("translated_text", "").strip(),
                    "detected_language": result.get("detected_language", ""),
                    "target_language": result.get("target_language", target_language),
                }
            except Exception:
                pass
        detected = "zh" if re.search(r"[一-鿿]", text) else "en"
        return {
            "translated_text": text,
            "detected_language": detected,
            "target_language": target_language,
        }
