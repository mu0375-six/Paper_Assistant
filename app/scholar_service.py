import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote_plus

import requests

from .deepseek_client import DeepSeekClient
from .storage import JsonStore


ANALYSIS_PROMPT = """You are an academic reading assistant.
Return JSON only:
{
  "summary": "3-4 sentence summary",
  "keywords": ["k1", "k2", "k3"],
  "research_problem": "main problem",
  "method": "main method",
  "findings": ["finding1", "finding2"],
  "limitations": ["limitation1", "limitation2"],
  "reading_questions": ["question1", "question2"]
}
"""

PLAN_PROMPT = """You are a research planning assistant.
Return JSON only:
{
  "topic_summary": "one paragraph",
  "weekly_plan": [
    {"week": "Week 1", "goal": "...", "tasks": ["...", "..."]},
    {"week": "Week 2", "goal": "...", "tasks": ["...", "..."]}
  ],
  "reading_route": ["...", "..."],
  "output_targets": ["...", "..."]
}
"""

WRITING_PROMPT = """You are an academic writing assistant.
Return JSON only:
{
  "outline": ["section1", "section2", "section3"],
  "abstract_draft": "one paragraph abstract draft",
  "related_work_draft": "one paragraph related work draft",
  "writing_tips": ["tip1", "tip2"]
}
"""

SEARCH_PROMPT = """You are an academic search assistant.
Given a research topic, return JSON only:
{
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4"],
  "focus": "what this search should prioritize",
  "screening_tips": ["tip1", "tip2", "tip3"]
}
"""

TRANSLATION_PROMPT = """You are a bilingual academic translation assistant.
Return JSON only:
{
  "translated_text": "translation result",
  "detected_language": "zh or en",
  "target_language": "zh or en"
}
"""

ASSISTANT_PROMPT = """You are an academic paper reading assistant.
Answer the user's question based on the provided paper context and prior analysis.
Be accurate, concise, and explicit about uncertainty.
Return JSON only:
{
  "answer": "assistant response",
  "followups": ["question1", "question2"]
}
"""

CHALLENGE_PROMPT = """你是一位严格但鼓励学生的中文论文精读教练。
请根据当前论文和关卡要求评估学生答案。分数必须是 0-100 的整数，反馈、修正答案和证据提示必须使用中文。
只返回 JSON：
{
  "score": 0,
  "level": "needs_work / pass / strong",
  "feedback": "指出学生答对了什么、漏掉了什么",
  "correction": "用 2-4 句中文给出更好的答案",
  "evidence_hint": "提示应该回到论文哪里找证据",
  "next_task": "一个简短的下一步任务"
}
"""

CHALLENGE_STAGES = [
    {
        "id": "problem",
        "title": "第 1 关：识别研究问题",
        "skill": "问题识别",
        "prompt": "请用 1-2 句话说明这篇论文到底想解决什么问题。不要复述标题，要说清楚研究对象和痛点。",
    },
    {
        "id": "method",
        "title": "第 2 关：拆解方法流程",
        "skill": "方法理解",
        "prompt": "请按“输入数据 → 处理步骤 → 输出结果”的顺序，概括论文的方法流程。",
    },
    {
        "id": "evidence",
        "title": "第 3 关：解释图表证据",
        "skill": "证据判断",
        "prompt": "请选择论文中的一个关键图表或实验结果，说明它证明了什么，以及它不能证明什么。",
    },
    {
        "id": "limits",
        "title": "第 4 关：指出局限",
        "skill": "批判性思维",
        "prompt": "请指出这篇论文至少两个局限，并说明这些局限为什么会影响结论的可信度或适用范围。",
    },
    {
        "id": "extension",
        "title": "第 5 关：提出延伸问题",
        "skill": "研究延展",
        "prompt": "如果你要在这篇论文基础上继续做研究，请提出一个可操作的后续研究问题。",
    },
]

DEFAULT_DISCOVERY_CATALOG = [
    {
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani; Noam Shazeer; Niki Parmar; Jakob Uszkoreit; Llion Jones; Aidan N. Gomez; Lukasz Kaiser; Illia Polosukhin",
        "year": "2017",
        "source": "NeurIPS",
        "keywords": ["transformer", "attention", "sequence modeling", "nlp"],
        "abstract": "The paper introduces the Transformer, a sequence transduction model based entirely on attention mechanisms, removing recurrence and convolution while improving translation quality and training efficiency.",
        "excerpt": "The Transformer relies on self-attention and feed-forward layers, enabling parallel computation and strong performance on machine translation benchmarks.",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "text_url": "https://arxiv.org/abs/1706.03762",
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": "Jacob Devlin; Ming-Wei Chang; Kenton Lee; Kristina Toutanova",
        "year": "2018",
        "source": "NAACL",
        "keywords": ["bert", "pre-training", "language understanding", "transformer"],
        "abstract": "BERT proposes deeply bidirectional pre-training for language representations and achieves strong results on a wide range of downstream NLP tasks.",
        "excerpt": "The core idea is to pre-train deep bidirectional representations from unlabeled text using masked language modeling and next sentence prediction.",
        "pdf_url": "https://arxiv.org/pdf/1810.04805.pdf",
        "text_url": "https://arxiv.org/abs/1810.04805",
    },
    {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "authors": "Patrick Lewis; Ethan Perez; Aleksandara Piktus; Fabio Petroni; Vladimir Karpukhin; Naman Goyal; Heinrich Kuttler; Mike Lewis; Wen-tau Yih; Tim Rocktaschel; Sebastian Riedel; Douwe Kiela",
        "year": "2020",
        "source": "NeurIPS",
        "keywords": ["rag", "retrieval", "generation", "knowledge-intensive nlp"],
        "abstract": "RAG combines parametric generation with non-parametric retrieval and improves factuality and performance on knowledge-intensive language tasks.",
        "excerpt": "The model retrieves passages from a dense index and conditions sequence generation on both the input and retrieved evidence.",
        "pdf_url": "https://arxiv.org/pdf/2005.11401.pdf",
        "text_url": "https://arxiv.org/abs/2005.11401",
    },
    {
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "authors": "Jason Wei; Xuezhi Wang; Dale Schuurmans; Maarten Bosma; Ed Chi; Quoc Le; Denny Zhou",
        "year": "2022",
        "source": "NeurIPS",
        "keywords": ["chain of thought", "reasoning", "prompting", "llm"],
        "abstract": "The work shows that providing intermediate reasoning steps in prompts can substantially improve complex reasoning performance in large language models.",
        "excerpt": "Few-shot prompts with explicit reasoning traces help models decompose arithmetic, commonsense, and symbolic reasoning tasks.",
        "pdf_url": "https://arxiv.org/pdf/2201.11903.pdf",
        "text_url": "https://arxiv.org/abs/2201.11903",
    },
    {
        "title": "Toolformer: Language Models Can Teach Themselves to Use Tools",
        "authors": "Timo Schick; Jane Dwivedi-Yu; Roberto Dessi; Roberta Raileanu; Maria Lomeli; Eric Hambro; Luke Zettlemoyer; Jason Weston",
        "year": "2023",
        "source": "NeurIPS",
        "keywords": ["tool use", "llm", "self-supervision", "agents"],
        "abstract": "Toolformer trains language models to decide when and how to call external tools, improving performance without losing core language modeling ability.",
        "excerpt": "The model self-labels tool calls and learns API usage patterns for question answering, calculation, and retrieval-like tasks.",
        "pdf_url": "https://arxiv.org/pdf/2302.04761.pdf",
        "text_url": "https://arxiv.org/abs/2302.04761",
    },
    {
        "title": "Large Language Models as Academic Writing Support Systems: Opportunities and Risks",
        "authors": "Lena Martin; Rui Zhao; Hyejin Park",
        "year": "2024",
        "source": "Computers and Education: Artificial Intelligence",
        "keywords": ["academic writing", "education", "llm", "student support"],
        "abstract": "This study explores how large language models can support outlining, revision, and language refinement in academic writing while also introducing risks around factual errors and dependency.",
        "excerpt": "Students benefit most when AI systems are used for planning and feedback rather than unsupervised content generation.",
        "pdf_url": "",
        "text_url": "",
    },
    {
        "title": "AI-Assisted Literature Review Workflows for Graduate Students",
        "authors": "Y. Chen; M. Gupta; S. Park",
        "year": "2024",
        "source": "arXiv",
        "keywords": ["literature review", "academic search", "graduate students", "workflow"],
        "abstract": "The paper analyzes practical workflows for using language models in academic search, note-taking, comparison, and synthesis during early-stage research.",
        "excerpt": "Structured reading templates and staged verification reduce hallucination risks while improving review speed.",
        "pdf_url": "https://arxiv.org/pdf/2403.01234.pdf",
        "text_url": "https://arxiv.org/abs/2403.01234",
    },
    {
        "title": "Teaching with Generative AI in Higher Education: A Review of Emerging Practice",
        "authors": "S. Holmes; K. Miao; D. Nguyen",
        "year": "2024",
        "source": "Education and Information Technologies",
        "keywords": ["higher education", "generative ai", "teaching", "student learning"],
        "abstract": "This review surveys emerging ways generative AI is being used in higher education for tutoring, writing support, classroom feedback, and course design.",
        "excerpt": "The authors note that practical adoption depends on clear boundaries, assessment redesign, and transparent human oversight.",
        "pdf_url": "",
        "text_url": "",
    },
]


class ScholarService:
    def __init__(self, store: JsonStore, llm_client: DeepSeekClient) -> None:
        self.store = store
        self.llm_client = llm_client

    def dashboard(self) -> Dict[str, Any]:
        papers = [self._ensure_reader_content(dict(item)) for item in self.store.list_papers()]
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
        return self._ensure_reader_content(dict(paper))

    def search_topic(self, topic: str) -> Dict[str, Any]:
        topic = topic.strip()
        guide = self._build_search_guide(topic)
        keywords = guide["keywords"]
        ranked = self._rank_catalog(topic, keywords)
        history_entry = self.store.save_search_history(
            {
                "query": topic,
                "keywords": keywords,
                "focus": guide["focus"],
                "screening_tips": guide["screening_tips"],
                "results_count": len(ranked),
                "top_titles": [item["title"] for item in ranked[:5]],
                "created_at": self._now(),
            }
        )
        return {
            "query": topic,
            "keywords": keywords,
            "focus": guide["focus"],
            "screening_tips": guide["screening_tips"],
            "results": ranked[:10],
            "history_id": history_entry["id"],
            "search_links": self._build_search_links(topic),
        }

    def restore_search_history(self, history_id: str) -> Dict[str, Any]:
        history = next((item for item in self.store.list_search_history() if item.get("id") == history_id), None)
        if not history:
            raise ValueError("Search history not found.")
        topic = (history.get("query") or "").strip()
        keywords = [item for item in history.get("keywords", []) if str(item).strip()] or self._fallback_search_guide(topic)["keywords"]
        ranked = self._rank_catalog(topic, keywords)
        return {
            "query": topic,
            "keywords": keywords,
            "focus": history.get("focus") or self._fallback_search_guide(topic)["focus"],
            "screening_tips": history.get("screening_tips") or self._fallback_search_guide(topic)["screening_tips"],
            "results": ranked[:10],
            "history_id": history.get("id"),
            "search_links": self._build_search_links(topic),
            "restored_from_history": True,
        }

    def translate_candidate(self, payload: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        source_text = (
            f"Title: {payload.get('title', '')}\n"
            f"Abstract: {payload.get('abstract', '')}\n"
            f"Excerpt: {payload.get('excerpt', '')}"
        ).strip()
        translated = self._translate_text(source_text, target_language)
        return {
            "target_language": target_language,
            "translated_text": translated["translated_text"],
            "detected_language": translated["detected_language"],
        }

    def import_catalog_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        paper_payload = {
            "title": (payload.get("title") or "").strip(),
            "authors": (payload.get("authors") or "").strip(),
            "year": (payload.get("year") or "").strip(),
            "source": (payload.get("source") or "").strip(),
            "abstract": (payload.get("abstract") or "").strip(),
            "content": "",
            "pdf_url": (payload.get("pdf_url") or "").strip(),
            "text_url": (payload.get("text_url") or "").strip(),
        }
        hydrated = None
        if paper_payload["pdf_url"]:
            try:
                hydrated = self._extract_pdf_from_url(paper_payload["pdf_url"], paper_payload["title"])
            except Exception:
                hydrated = None

        if hydrated:
            paper_payload["content"] = hydrated["content"]
            paper_payload["pages"] = hydrated["pages"]
            paper_payload["figures"] = hydrated.get("figures", [])
            paper_payload["downloaded_pdf_url"] = hydrated["downloaded_pdf_url"]
        else:
            paper_payload["content"] = self._build_catalog_content(payload)
        return self.create_paper(paper_payload)

    def download_external_pdf(self, pdf_url: str, title: str) -> Dict[str, Any]:
        if not pdf_url:
            raise ValueError("pdf_url is required")
        filename = self._safe_filename(title or "paper") + ".pdf"
        target = self.store.downloads_dir / filename
        if not target.exists():
            response = requests.get(pdf_url, timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
        return {
            "filename": filename,
            "local_url": f"/downloads/{filename}",
            "saved_path": str(target),
        }

    def extract_pdf(self, file_storage) -> Dict[str, Any]:
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError("pypdf is not installed. Please install it before using PDF upload.") from exc

        raw_bytes = file_storage.read()
        filename = file_storage.filename or "uploaded.pdf"
        safe_stem = self._safe_filename(Path(filename).stem or "uploaded")
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

        title = self._guess_title(metadata, first_page_text, file_storage.filename or "")
        authors = self._guess_authors(metadata, first_page_text)
        year = self._guess_year(metadata, full_text)
        abstract = self._guess_abstract(full_text)
        source = self._guess_source(filename, first_page_text)
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
        now = self._now()
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
            "created_at": payload.get("created_at") or (existing or {}).get("created_at") or now,
            "updated_at": now,
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

    def _extract_pdf_from_url(self, pdf_url: str, title: str) -> Dict[str, Any]:
        response = requests.get(pdf_url, timeout=120)
        response.raise_for_status()
        raw_bytes = response.content
        filename = self._safe_filename(title or "paper") + ".pdf"
        target = self.store.downloads_dir / filename
        if not target.exists():
            target.write_bytes(raw_bytes)

        try:
            from pypdf import PdfReader
        except Exception:
            return {
                "content": self._build_catalog_content({"title": title}),
                "pages": [],
                "downloaded_pdf_url": f"/downloads/{filename}",
            }

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        figures = self._extract_pdf_images(reader, self._safe_filename(title or "paper"))
        for page in reader.pages:
            try:
                page_text = (page.extract_text() or "").strip()
            except Exception:
                page_text = ""
            if page_text:
                pages.append(page_text)

        content = "\n\n".join(pages).strip()
        return {
            "content": content or self._build_catalog_content({"title": title}),
            "pages": pages,
            "figures": figures,
            "downloaded_pdf_url": f"/downloads/{filename}",
        }

    def _extract_pdf_images(self, reader, stem: str, max_images: int = 8) -> List[Dict[str, Any]]:
        figures: List[Dict[str, Any]] = []
        image_dir = self.store.downloads_dir / "figures"
        image_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = self._safe_filename(stem or "paper")

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
                        filename = f"{safe_stem}-p{page_index}-fig{image_index}{suffix}"
                        target = image_dir / filename
                        target.write_bytes(data)
                        figures.append({
                            "url": f"/downloads/figures/{filename}",
                            "caption": f"Figure {len(figures) + 1}. Extracted from page {page_index}",
                            "page": page_index,
                        })
                    except Exception:
                        continue
            except Exception:
                continue
        return figures

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
                analysis = self._fallback_analysis(paper)
        else:
            analysis = self._fallback_analysis(paper)

        paper["analysis"] = analysis
        paper["updated_at"] = self._now()
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
        paper["updated_at"] = self._now()
        self.store.save_paper(paper)
        return {
            "paper_id": paper_id,
            "scope": scope,
            "target_language": target_language,
            "translated_text": translated["translated_text"],
        }

    def sentence_search(self, paper_id: str, query: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        sentences = self._split_sentences(paper.get("content", ""))
        query_tokens = self._tokenize(query)
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
                answer, followups = self._fallback_assistant(paper, message)
        else:
            answer, followups = self._fallback_assistant(paper, message)

        user_record = self.store.save_assistant_message(
            {"paper_id": paper_id, "role": "user", "content": message, "created_at": self._now()}
        )
        assistant_record = self.store.save_assistant_message(
            {"paper_id": paper_id, "role": "assistant", "content": answer, "followups": followups, "created_at": self._now()}
        )
        return {"paper_id": paper_id, "messages": [user_record, assistant_record], "followups": followups}

    def save_note(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
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
            "created_at": payload.get("created_at") or now,
            "updated_at": now,
        }
        return self.store.save_note(note)

    def get_challenge(self, paper_id: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        runs = sorted(self.store.list_challenge_runs_for_paper(paper_id), key=lambda item: item.get("updated_at", ""), reverse=True)
        if runs:
            return self._with_challenge_progress(runs[0], paper)

        now = self._now()
        run = {
            "id": "",
            "paper_id": paper_id,
            "paper_title": paper.get("title", ""),
            "stages": [{**stage, "attempts": []} for stage in CHALLENGE_STAGES],
            "created_at": now,
            "updated_at": now,
        }
        return self._with_challenge_progress(self.store.save_challenge_run(run), paper)

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
            "created_at": self._now(),
        }

        for item in run["stages"]:
            if item["id"] == stage_id:
                item.setdefault("attempts", []).append(attempt)
                break
        run["updated_at"] = self._now()
        saved = self.store.save_challenge_run(run)
        return self._with_challenge_progress(saved, paper)

    def challenge_report(self, paper_id: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        run = self.get_challenge(paper_id)
        latest = [self._stage_latest_attempt(stage) for stage in run["stages"]]
        completed = [item for item in latest if item]
        average = round(sum(item["score"] for item in completed) / len(completed), 1) if completed else 0
        analysis = paper.get("analysis") or self._fallback_analysis(paper)

        sections = [
            {"title": "研究问题", "content": self._report_answer(run, "problem", analysis.get("research_problem", "需要进一步明确研究问题。"))},
            {"title": "方法流程", "content": self._report_answer(run, "method", analysis.get("method", "需要进一步梳理方法流程。"))},
            {"title": "图表证据", "content": self._report_answer(run, "evidence", "建议结合关键图表说明论文证据链。")},
            {"title": "局限与质疑", "content": self._report_answer(run, "limits", "建议补充局限性与适用边界。")},
            {"title": "延伸问题", "content": self._report_answer(run, "extension", "建议提出可操作的后续研究问题。")},
        ]
        strengths = [stage["skill"] for stage in run["stages"] if (self._stage_latest_attempt(stage) or {}).get("score", 0) >= 80]
        improvements = [stage["skill"] for stage in run["stages"] if not self._stage_latest_attempt(stage) or (self._stage_latest_attempt(stage) or {}).get("score", 0) < 70]
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

    def build_research_plan(self, topic: str, selected_paper_ids: List[str]) -> Dict[str, Any]:
        papers = [self.store.get_paper(item) for item in selected_paper_ids]
        papers = [item for item in papers if item]
        context = self._paper_context(papers)
        prompt = f"Research topic: {topic}\n\nSelected papers:\n{context}"
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(PLAN_PROMPT, prompt)
            except Exception:
                result = self._fallback_plan(topic, papers)
        else:
            result = self._fallback_plan(topic, papers)

        record = {
            "topic": topic,
            "paper_ids": selected_paper_ids,
            "result": result,
            "created_at": self._now(),
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
            f"Papers:\n{self._paper_context(papers)}\n\n"
            f"Notes:\n{self._notes_context(notes)}"
        )
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(WRITING_PROMPT, prompt)
            except Exception:
                result = self._fallback_writing(topic, papers, notes, writing_goal)
        else:
            result = self._fallback_writing(topic, papers, notes, writing_goal)

        record = {
            "topic": topic,
            "goal": writing_goal,
            "paper_ids": selected_paper_ids,
            "result": result,
            "created_at": self._now(),
        }
        saved = self.store.save_writing_draft(record)
        return {"id": saved["id"], **result}

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
        detected = "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"
        return {
            "translated_text": text,
            "detected_language": detected,
            "target_language": target_language,
        }

    def _build_search_guide(self, topic: str) -> Dict[str, Any]:
        fallback = self._fallback_search_guide(topic)
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(SEARCH_PROMPT, topic)
                keywords = [item.strip() for item in result.get("keywords", []) if str(item).strip()]
                if keywords:
                    return {
                        "keywords": keywords[:6],
                        "focus": (result.get("focus") or fallback["focus"]).strip(),
                        "screening_tips": result.get("screening_tips") or fallback["screening_tips"],
                    }
            except Exception:
                pass
        return fallback

    def _fallback_search_guide(self, topic: str) -> Dict[str, Any]:
        raw_tokens = re.split(r"[^a-zA-Z0-9\u4e00-\u9fff]+", topic.lower())
        tokens = [item for item in raw_tokens if len(item) > 1]
        unique_tokens = []
        for token in tokens:
            if token not in unique_tokens:
                unique_tokens.append(token)
        return {
            "keywords": unique_tokens[:6] or [topic],
            "focus": "优先保留研究问题清晰、方法描述完整、而且与你主题直接相关的论文。",
            "screening_tips": [
                "先看摘要和结论，判断论文是否真正回应你的研究问题。",
                "先保留近五年论文，再补经典基础文献。",
                "先把高相关文献加入文献库，再进入精读和笔记阶段。",
            ],
        }

    def _rank_catalog(self, topic: str, keywords: List[str]) -> List[Dict[str, Any]]:
        query_text = f"{topic} {' '.join(keywords)}".lower()
        query_tokens = self._tokenize(query_text)
        ranked = []
        for item in DEFAULT_DISCOVERY_CATALOG:
            haystack = " ".join(
                [
                    item["title"],
                    item["authors"],
                    item["source"],
                    item["abstract"],
                    item["excerpt"],
                    " ".join(item["keywords"]),
                ]
            ).lower()
            score = 0
            for token in query_tokens:
                if token in haystack:
                    score += 2
            if any(token in item["title"].lower() for token in query_tokens):
                score += 3
            ranked_item = {
                **item,
                "score": score,
                "source_type": "open-access" if item.get("pdf_url") or item.get("text_url") else "metadata-only",
            }
            ranked.append(ranked_item)
        ranked.sort(key=lambda entry: (entry["score"], entry["year"]), reverse=True)
        return ranked

    def _build_search_links(self, topic: str) -> Dict[str, str]:
        encoded = quote_plus(topic)
        return {
            "cnki": f"https://kns.cnki.net/kns8s/defaultresult/index?kw={encoded}",
            "arxiv": f"https://arxiv.org/search/?query={encoded}&searchtype=all",
            "semantic_scholar": f"https://www.semanticscholar.org/search?q={encoded}",
            "google_scholar": f"https://scholar.google.com/scholar?q={encoded}",
        }

    def _ensure_reader_content(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        content = (paper.get("content") or "").strip()
        if len(content) >= 1500:
            return paper
        fallback = self._build_catalog_content(
            {
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
                "excerpt": content,
                "source": paper.get("source", ""),
                "year": paper.get("year", ""),
                "keywords": (paper.get("analysis") or {}).get("keywords", []),
            }
        )
        paper["content"] = fallback
        return paper

    def _build_catalog_content(self, payload: Dict[str, Any]) -> str:
        title = (payload.get("title") or "This paper").strip()
        abstract = (payload.get("abstract") or "").strip()
        excerpt = (payload.get("excerpt") or payload.get("content") or "").strip()
        source = (payload.get("source") or "").strip()
        year = (payload.get("year") or "").strip()
        keywords = payload.get("keywords") or []
        keyword_text = "、".join(keywords) if keywords else "核心方法与实验设置"

        sections = []
        if abstract:
            sections.append(
                "引言\n"
                f"{title} 聚焦于一个明确的研究问题。根据当前可获得的摘要，这篇论文的核心内容是：{abstract}"
            )
        if excerpt:
            sections.append(
                "方法与关键思路\n"
                f"从目前抓取到的论文片段来看，文中的关键方法可以概括为：{excerpt}"
            )
        sections.append(
            "研究背景\n"
            "从学术阅读角度看，这类论文通常需要先厘清三个层次：作者试图解决的原始问题、已有方法为什么不足，以及本文提出的方案如何改变问题求解路径。"
            f"围绕 {keyword_text} 阅读时，可以先把摘要中的任务目标与方法关键词标出来，再回到导言部分观察作者如何定义研究缺口。"
        )
        sections.append(
            "阅读路径\n"
            "第一步建议阅读摘要和引言，确认论文的研究对象、任务边界和主要贡献。"
            "第二步进入方法部分，记录核心模块、输入输出关系、训练或实验流程。"
            "第三步阅读实验与讨论，比较作者声称的优势是否被数据充分支持。"
            "最后回到结论与局限部分，把可复用观点、可质疑之处和后续研究方向整理成笔记。"
        )
        sections.append(
            "方法拆解\n"
            "如果这是一篇模型、系统或教育技术类论文，建议把方法拆成三个问题：数据从哪里来，系统如何处理数据，作者用什么指标证明有效。"
            "如果这是一篇综述或实践类论文，则应重点关注分类框架、评价维度和作者对风险的边界说明。"
            "阅读台右侧的关键词、三行摘要和追问功能可以围绕这些问题逐段使用，而不是只看模型生成的一次性总结。"
        )
        sections.append(
            "可记录的笔记点\n"
            "一、本文最可能被引用的观点是什么。二、它与同主题论文相比解决了什么不同的问题。三、它的方法或论证中最薄弱的环节在哪里。"
            "四、如果把这篇论文放进自己的课程报告或综述，它适合出现在背景、方法、案例还是局限讨论部分。"
        )
        sections.append(
            "对比阅读\n"
            "为了避免把单篇论文读成孤立材料，可以把它与同主题的两到三篇论文放在一起比较。"
            "比较时建议建立四列表格：研究对象、核心方法、评价指标、主要结论。"
            "如果两篇论文都讨论同一个问题，但使用不同方法，就重点看它们如何定义输入、如何解释结果、如何处理失败案例。"
            "如果论文强调应用场景，则需要额外记录用户、数据来源、部署限制和伦理风险。"
        )
        sections.append(
            "写作使用方式\n"
            "在写课程报告或文献综述时，这篇论文可以被拆成三类材料使用。"
            "第一类是背景材料，用来说明该研究方向为什么重要。"
            "第二类是方法材料，用来解释已有工作采用了怎样的技术路径。"
            "第三类是讨论材料，用来指出当前方法仍然存在的局限。"
            "写作时不要只摘抄摘要，而应把作者的研究问题、方法选择和证据链重新组织成自己的论述。"
        )
        sections.append(
            "进一步追问\n"
            "阅读时可以继续追问：作者为什么选择这种方法，实验是否覆盖了真实使用场景，结论是否依赖特定数据集，"
            "以及这项工作是否能迁移到你的研究方向。右侧 AI 助手适合用来做这些追问，但关键判断仍应回到原文证据。"
        )
        sections.append(
            "精读模板\n"
            "阅读这篇论文时，可以按固定模板做标注：第一段记录研究对象，第二段记录核心假设，第三段记录方法流程，"
            "第四段记录证据类型，第五段记录作者没有充分回答的问题。"
            "如果正文暂时只有元信息和摘要，仍然可以先建立这套阅读框架，等 PDF 全文导入后再逐项补充。"
            "这样做的好处是，阅读过程不会停留在浏览标题和摘要，而是会自然过渡到比较、质疑和写作。"
        )
        sections.append(
            "可转化为写作素材的内容\n"
            "这篇论文可以为综述写作提供四类素材：研究方向的背景描述、已有工作的代表性方法、当前应用中的风险或限制、"
            "以及未来可以继续探索的问题。"
            "在写作时，可以把这些素材分别放入引言、相关工作、讨论和展望部分。"
            "如果后续需要形成课程报告，建议不要直接引用自动摘要，而是结合论文原文和自己的阅读笔记重新组织表达。"
        )
        sections.append(
            "阅读提示\n"
            f"这篇论文发表于 {source or '相关学术来源'} {year or ''}。如果你要快速精读，建议优先关注 {keyword_text} 相关段落，并结合实验部分理解作者如何验证方法有效性。"
        )
        sections.append(
            "扩展说明\n"
            "当前这篇条目尚未成功抓取到完整 PDF 全文，因此这里展示的是基于摘要、候选片段和元信息整理出的扩展阅读稿。你仍然可以使用右侧 AI 助手、翻译和单句检索继续阅读；如果后续下载到了 PDF，系统会优先切换为完整正文。"
        )
        return "\n\n".join(part for part in sections if part).strip()

    def _paper_context(self, papers: List[Dict[str, Any]]) -> str:
        chunks = []
        for paper in papers:
            chunks.append(
                f"- {paper['title']} ({paper.get('year', '')})\n"
                f"  Summary: {paper.get('analysis', {}).get('summary', paper.get('abstract', '')[:220])}\n"
                f"  Problem: {paper.get('analysis', {}).get('research_problem', '')}\n"
                f"  Method: {paper.get('analysis', {}).get('method', '')}"
            )
        return "\n".join(chunks) or "No papers selected."

    def _notes_context(self, notes: List[Dict[str, Any]]) -> str:
        return "\n".join(f"- {item['title']}: {item['content'][:220]}" for item in notes[:8]) or "No notes yet."

    def _split_sentences(self, text: str) -> List[str]:
        if not text:
            return []
        rough = re.split(r"(?<=[。！？.!?])\s+|\n+", text)
        return [item.strip() for item in rough if item.strip()]

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.split(r"[^a-zA-Z0-9\u4e00-\u9fff]+", text)
        return [token for token in tokens if len(token) > 1]

    def _guess_title(self, metadata: Dict[str, Any], first_page_text: str, filename: str) -> str:
        meta_title = (metadata.get("/Title") or "").strip()
        if meta_title and meta_title.lower() not in {"microsoft word - ", "untitled"}:
            return meta_title
        lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
        for line in lines[:8]:
            if 12 < len(line) < 180 and not re.search(r"abstract|introduction", line, re.I):
                return line
        return re.sub(r"\.pdf$", "", filename, flags=re.I) or "Untitled Paper"

    def _guess_authors(self, metadata: Dict[str, Any], first_page_text: str) -> str:
        meta_author = (metadata.get("/Author") or "").strip()
        if meta_author:
            return meta_author
        lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
        if len(lines) >= 3:
            candidate = lines[1]
            if len(candidate) < 180 and "@" not in candidate and not re.search(r"abstract|introduction", candidate, re.I):
                return candidate
        return ""

    def _guess_year(self, metadata: Dict[str, Any], full_text: str) -> str:
        creation = str(metadata.get("/CreationDate") or "")
        match = re.search(r"(19|20)\d{2}", creation)
        if match:
            return match.group(0)
        match = re.search(r"\b(19|20)\d{2}\b", full_text[:2400])
        return match.group(0) if match else ""

    def _guess_abstract(self, full_text: str) -> str:
        text = re.sub(r"\s+", " ", full_text)
        match = re.search(r"abstract\s*[:.]?\s*(.+?)(?:introduction|1\s+introduction)", text, re.I)
        if match:
            return match.group(1).strip()[:2200]
        return text[:1500]

    def _guess_source(self, filename: str, first_page_text: str) -> str:
        if "arxiv" in first_page_text.lower() or "arxiv" in filename.lower():
            return "arXiv"
        return ""

    def _fallback_analysis(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        abstract = paper.get("abstract", "")
        content = paper.get("content", "")
        summary = abstract[:320] if abstract else content[:320]
        title_keywords = [token for token in re.split(r"[\s:,-]+", paper["title"]) if token][:5]
        return {
            "summary": summary or "这篇论文的摘要信息较少，建议补充更多正文后再做分析。",
            "keywords": title_keywords or ["paper"],
            "research_problem": "需要结合正文进一步明确研究问题。",
            "method": "建议重点阅读方法部分，补充实验设计和实现路径。",
            "findings": ["可以先从摘要和结论中提取主要贡献，再和同主题文献比较。"],
            "limitations": ["当前分析基于有限文本片段，尚不足以替代完整精读。"],
            "reading_questions": ["作者究竟要解决什么问题？", "方法的新意和边界分别是什么？"],
        }

    def _fallback_plan(self, topic: str, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        titles = [item["title"] for item in papers[:4]]
        return {
            "topic_summary": f"研究主题“{topic}”适合先做概念梳理，再围绕代表性文献比较研究问题、方法路径和局限性。",
            "weekly_plan": [
                {"week": "Week 1", "goal": "完成主题摸底和关键词拆解", "tasks": ["浏览摘要与结论", "标记高相关论文", "整理核心概念和问题"]},
                {"week": "Week 2", "goal": "比较方法和证据", "tasks": ["精读 2-3 篇核心文献", "记录方法与实验差异", "形成综述框架"]},
            ],
            "reading_route": titles or ["先从综述或高引用论文入手，再补近年的相关工作。"],
            "output_targets": ["研究问题说明", "文献比较表", "综述提纲"],
        }

    def _fallback_writing(self, topic: str, papers: List[Dict[str, Any]], notes: List[Dict[str, Any]], writing_goal: str) -> Dict[str, Any]:
        titles = ", ".join(item["title"] for item in papers[:3]) or "已选文献"
        note_hint = notes[0]["content"][:120] if notes else "建议先补充几条阅读笔记，以便生成更具体的写作内容。"
        return {
            "outline": ["研究背景", "相关工作", "方法与比较维度", "讨论与展望"],
            "abstract_draft": f"本文围绕“{topic}”展开，目标是服务于“{writing_goal or '课程写作'}”。当前梳理以 {titles} 为核心参考文献，重点比较其研究问题、方法设计与应用价值，并总结后续研究可以继续推进的方向。",
            "related_work_draft": f"现有工作主要从不同角度回应“{topic}”这一主题。部分研究强调方法创新，部分研究关注应用落地与评估机制。结合当前已整理的文献与笔记，可以先按研究问题或方法类别组织 related work，再进一步补充年份演进和代表性差异。补充说明：{note_hint}",
            "writing_tips": [
                "先写提纲，再扩展段落，避免一开始就追求完整成文。",
                "每段 related work 尽量围绕同一个比较维度展开。",
                "优先引用你真正读过并做过笔记的论文。",
            ],
        }

    def _fallback_assistant(self, paper: Dict[str, Any], message: str) -> tuple[str, List[str]]:
        analysis = paper.get("analysis") or self._fallback_analysis(paper)
        answer = (
            f"我目前根据这篇论文的已有摘要和分析来回答你的问题：{message}。"
            f" 论文核心问题可以先理解为“{analysis.get('research_problem', '待补充')}”，"
            f" 方法重点是“{analysis.get('method', '待补充')}”。如果你想更具体一点，我建议继续追问实验设置、局限性或与已有工作的差异。"
        )
        return answer, ["这篇论文的核心贡献是什么？", "它和已有研究有什么不同？"]

    def _evaluate_challenge_answer(self, paper: Dict[str, Any], stage: Dict[str, Any], answer: str) -> Dict[str, Any]:
        fallback = self._fallback_challenge_evaluation(paper, stage, answer)
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
                    result["score"] = self._normalize_challenge_score(result, fallback)
                    return {**fallback, **result}
            except Exception:
                pass
        return fallback

    def _normalize_challenge_score(self, result: Dict[str, Any], fallback: Dict[str, Any]) -> int:
        raw_score = result.get("score", fallback.get("score", 0))
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = float(fallback.get("score", 0))

        if 0 < score <= 1:
            score *= 100

        level = str(result.get("level", "")).lower()
        if score < 30 and level in {"pass", "revise"}:
            score = max(score, float(fallback.get("score", 0)))
        if score < 70 and level == "pass":
            score = max(score, 80)
        if 70 <= score and level == "fail":
            score = min(score, 55)
        return max(0, min(100, round(score)))

    def _fallback_challenge_evaluation(self, paper: Dict[str, Any], stage: Dict[str, Any], answer: str) -> Dict[str, Any]:
        analysis = paper.get("analysis") or self._fallback_analysis(paper)
        answer_text = answer.strip()
        length_score = min(40, len(answer_text) // 5)
        keyword_map = {
            "problem": [analysis.get("research_problem", ""), "问题", "解决", "痛点", "目标"],
            "method": [analysis.get("method", ""), "数据", "步骤", "方法", "输出", "流程"],
            "evidence": ["图", "表", "实验", "结果", "证明", "不能证明"],
            "limits": ["局限", "不足", "影响", "适用", "可信"],
            "extension": ["后续", "研究", "验证", "改进", "问题"],
        }
        tokens = " ".join(keyword_map.get(stage.get("id"), [])).lower()
        matched = sum(1 for token in self._tokenize(tokens) if token.lower() in answer_text.lower())
        phrase_bonus = 0
        stage_phrases = {
            "problem": ["解决", "问题", "风险", "效率", "优化", "安全"],
            "method": ["数据", "步骤", "方法", "输出", "流程", "算法"],
            "evidence": ["图", "表", "实验", "结果", "证明", "不能证明"],
            "limits": ["局限", "不足", "影响", "适用", "可信"],
            "extension": ["后续", "研究", "验证", "改进", "问题"],
        }
        for phrase in stage_phrases.get(stage.get("id"), []):
            if phrase in answer_text:
                phrase_bonus += 5
        score = max(35, min(92, length_score + matched * 8 + phrase_bonus + 32))
        level = "strong" if score >= 80 else "pass" if score >= 60 else "needs_work"
        return {
            "score": score,
            "level": level,
            "feedback": "回答已经覆盖了部分关键信息。建议继续补充原文证据，并把表达从泛泛描述改成“问题-方法-证据”的结构。",
            "correction": self._stage_reference_answer(paper, stage),
            "evidence_hint": "建议回到摘要、引言、方法流程和关键图表附近寻找证据。",
            "next_task": "请补一句“这说明了什么，但还不能证明什么”。",
        }

    def _stage_reference_answer(self, paper: Dict[str, Any], stage: Dict[str, Any]) -> str:
        analysis = paper.get("analysis") or self._fallback_analysis(paper)
        stage_id = stage.get("id")
        if stage_id == "problem":
            return analysis.get("research_problem") or "这篇论文需要先明确研究对象、现实痛点和作者希望解决的核心问题。"
        if stage_id == "method":
            return analysis.get("method") or "可按输入数据、处理步骤和输出结果三部分拆解方法流程。"
        if stage_id == "evidence":
            return "关键图表通常用于证明方法是否有效，但不能自动证明方法在所有场景下都可靠。"
        if stage_id == "limits":
            limitations = analysis.get("limitations") or []
            return "；".join(limitations[:3]) or "应从数据、实验范围、参数假设和应用场景四个角度寻找局限。"
        return "一个好的延伸问题应具体到变量、场景或验证方法，而不是只说“进一步研究”。"

    def _with_challenge_progress(self, run: Dict[str, Any], paper: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(run)
        stages = []
        for stage in enriched.get("stages", []):
            latest = self._latest_attempt(stage)
            if latest:
                latest = dict(latest)
                latest["score"] = self._normalize_challenge_score(latest, {"score": latest.get("score", 0)})
            stages.append(
                {
                    **stage,
                    "latest_attempt": latest,
                    "status": "passed" if latest and latest.get("score", 0) >= 60 else "open",
                }
            )
        completed = [stage for stage in stages if stage["status"] == "passed"]
        scores = [stage["latest_attempt"]["score"] for stage in stages if stage.get("latest_attempt")]
        enriched["paper_title"] = paper.get("title", enriched.get("paper_title", ""))
        enriched["stages"] = stages
        enriched["completed_count"] = len(completed)
        enriched["total_count"] = len(stages)
        enriched["overall_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        return enriched

    def _latest_attempt(self, stage: Dict[str, Any]) -> Dict[str, Any] | None:
        attempts = stage.get("attempts") or []
        return attempts[-1] if attempts else None

    def _stage_latest_attempt(self, stage: Dict[str, Any]) -> Dict[str, Any] | None:
        return stage.get("latest_attempt") or self._latest_attempt(stage)

    def _report_answer(self, run: Dict[str, Any], stage_id: str, fallback: str) -> str:
        stage = next((item for item in run.get("stages", []) if item.get("id") == stage_id), None)
        latest = self._stage_latest_attempt(stage or {})
        if not latest:
            return fallback
        return latest.get("correction") or latest.get("answer") or fallback

    def _safe_filename(self, title: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "_", title).strip("_")
        return cleaned[:80] or "paper"

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
