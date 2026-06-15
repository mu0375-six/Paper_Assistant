"""纯工具函数：不依赖 self.store / self.llm_client 的辅助方法。

拆分自 scholar_service.py，供各 Mixin 或外部模块直接调用。
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from .constants import DEFAULT_DISCOVERY_CATALOG


# ── 通用工具 ───────────────────────────────────────────────


def now() -> str:
    """返回当前时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def tokenize(text: str) -> List[str]:
    """中英文混合分词，返回长度 > 1 的词元列表。"""
    tokens = re.split(r"[^a-zA-Z0-9一-鿿]+", text)
    return [token for token in tokens if len(token) > 1]


def safe_filename(title: str) -> str:
    """将标题转换为安全的文件名。"""
    cleaned = re.sub(r"[^a-zA-Z0-9一-鿿_-]+", "_", title).strip("_")
    return cleaned[:80] or "paper"


def split_sentences(text: str) -> List[str]:
    """按中英文标点拆分句子。"""
    if not text:
        return []
    rough = re.split(r"(?<=[。！？.!?])\s+|\n+", text)
    return [item.strip() for item in rough if item.strip()]


# ── Fallback 生成（不依赖 LLM） ────────────────────────────


def fallback_analysis(paper: Dict[str, Any]) -> Dict[str, Any]:
    """当 LLM 不可用时，基于论文文本生成简易分析。"""
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


def fallback_assistant(paper: Dict[str, Any], message: str) -> tuple:
    """当 LLM 不可用时，基于论文已有信息生成简易回答。"""
    analysis = paper.get("analysis") or fallback_analysis(paper)
    answer = (
        f"我目前根据这篇论文的已有摘要和分析来回答你的问题：{message}。"
        f" 论文核心问题可以先理解为「{analysis.get('research_problem', '待补充')}」，"
        f" 方法重点是「{analysis.get('method', '待补充')}」。如果你想更具体一点，我建议继续追问实验设置、局限性或与已有工作的差异。"
    )
    return answer, ["这篇论文的核心贡献是什么？", "它和已有研究有什么不同？"]


def fallback_plan(topic: str, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """当 LLM 不可用时，生成简易研究计划。"""
    titles = [item["title"] for item in papers[:4]]
    return {
        "topic_summary": f"研究主题「{topic}」适合先做概念梳理，再围绕代表性文献比较研究问题、方法路径和局限性。",
        "weekly_plan": [
            {"week": "Week 1", "goal": "完成主题摸底和关键词拆解", "tasks": ["浏览摘要与结论", "标记高相关论文", "整理核心概念和问题"]},
            {"week": "Week 2", "goal": "比较方法和证据", "tasks": ["精读 2-3 篇核心文献", "记录方法与实验差异", "形成综述框架"]},
        ],
        "reading_route": titles or ["先从综述或高引用论文入手，再补近年的相关工作。"],
        "output_targets": ["研究问题说明", "文献比较表", "综述提纲"],
    }


def fallback_writing(
    topic: str,
    papers: List[Dict[str, Any]],
    notes: List[Dict[str, Any]],
    writing_goal: str,
) -> Dict[str, Any]:
    """当 LLM 不可用时，生成简易写作包。"""
    titles = ", ".join(item["title"] for item in papers[:3]) or "已选文献"
    note_hint = notes[0]["content"][:120] if notes else "建议先补充几条阅读笔记，以便生成更具体的写作内容。"
    return {
        "outline": ["研究背景", "相关工作", "方法与比较维度", "讨论与展望"],
        "abstract_draft": f"本文围绕「{topic}」展开，目标是服务于「{writing_goal or '课程写作'}」。当前梳理以 {titles} 为核心参考文献，重点比较其研究问题、方法设计与应用价值，并总结后续研究可以继续推进的方向。",
        "related_work_draft": f"现有工作主要从不同角度回应「{topic}」这一主题。部分研究强调方法创新，部分研究关注应用落地与评估机制。结合当前已整理的文献与笔记，可以先按研究问题或方法类别组织 related work，再进一步补充年份演进和代表性差异。补充说明：{note_hint}",
        "writing_tips": [
            "先写提纲，再扩展段落，避免一开始就追求完整成文。",
            "每段 related work 尽量围绕同一个比较维度展开。",
            "优先引用你真正读过并做过笔记的论文。",
        ],
    }


def fallback_challenge_evaluation(
    paper: Dict[str, Any],
    stage: Dict[str, Any],
    answer: str,
) -> Dict[str, Any]:
    """当 LLM 不可用时，基于规则生成闯关评分。"""
    analysis = paper.get("analysis") or fallback_analysis(paper)
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
    matched = sum(1 for token in tokenize(tokens) if token.lower() in answer_text.lower())
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
        "feedback": "回答已经覆盖了部分关键信息。建议继续补充原文证据，并把表达从泛泛描述改成「问题-方法-证据」的结构。",
        "correction": stage_reference_answer(paper, stage),
        "evidence_hint": "建议回到摘要、引言、方法流程和关键图表附近寻找证据。",
        "next_task": "请补一句「这说明了什么，但还不能证明什么」。",
    }


def stage_reference_answer(paper: Dict[str, Any], stage: Dict[str, Any]) -> str:
    """生成闯关参考答案。"""
    analysis = paper.get("analysis") or fallback_analysis(paper)
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
    return "一个好的延伸问题应具体到变量、场景或验证方法，而不是只说「进一步研究」。"


def normalize_challenge_score(result: Dict[str, Any], fallback: Dict[str, Any]) -> int:
    """将模型返回的分数归一化到 0-100 范围。"""
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


# ── 闯关进度相关 ───────────────────────────────────────────


def latest_attempt(stage: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """获取关卡最近一次作答。"""
    attempts = stage.get("attempts") or []
    return attempts[-1] if attempts else None


def stage_latest_attempt(stage: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """获取关卡最近一次作答（兼容 enriched 与原始格式）。"""
    return stage.get("latest_attempt") or latest_attempt(stage)


def with_challenge_progress(run: Dict[str, Any], paper: Dict[str, Any]) -> Dict[str, Any]:
    """为闯关运行添加进度信息。"""
    enriched = dict(run)
    stages = []
    for stage in enriched.get("stages", []):
        latest = latest_attempt(stage)
        if latest:
            latest = dict(latest)
            latest["score"] = normalize_challenge_score(latest, {"score": latest.get("score", 0)})
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


def report_answer(run: Dict[str, Any], stage_id: str, fallback: str) -> str:
    """从闯关运行中提取某个关卡的汇报答案。"""
    stage = next((item for item in run.get("stages", []) if item.get("id") == stage_id), None)
    latest = stage_latest_attempt(stage or {})
    if not latest:
        return fallback
    return latest.get("correction") or latest.get("answer") or fallback


# ── PDF 元信息猜测 ─────────────────────────────────────────


def guess_title(metadata: Dict[str, Any], first_page_text: str, filename: str) -> str:
    """从 PDF 元数据或首页文本猜测论文标题。"""
    meta_title = (metadata.get("/Title") or "").strip()
    if meta_title and meta_title.lower() not in {"microsoft word - ", "untitled"}:
        return meta_title
    lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
    for line in lines[:8]:
        if 12 < len(line) < 180 and not re.search(r"abstract|introduction", line, re.I):
            return line
    return re.sub(r"\.pdf$", "", filename, flags=re.I) or "Untitled Paper"


def guess_authors(metadata: Dict[str, Any], first_page_text: str) -> str:
    """从 PDF 元数据或首页文本猜测作者。"""
    meta_author = (metadata.get("/Author") or "").strip()
    if meta_author:
        return meta_author
    lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
    if len(lines) >= 3:
        candidate = lines[1]
        if len(candidate) < 180 and "@" not in candidate and not re.search(r"abstract|introduction", candidate, re.I):
            return candidate
    return ""


def guess_year(metadata: Dict[str, Any], full_text: str) -> str:
    """从 PDF 元数据或正文猜测年份。"""
    creation = str(metadata.get("/CreationDate") or "")
    match = re.search(r"(19|20)\d{2}", creation)
    if match:
        return match.group(0)
    match = re.search(r"\b(19|20)\d{2}\b", full_text[:2400])
    return match.group(0) if match else ""


def guess_abstract(full_text: str) -> str:
    """从正文猜测摘要。"""
    text = re.sub(r"\s+", " ", full_text)
    match = re.search(r"abstract\s*[:.]?\s*(.+?)(?:introduction|1\s+introduction)", text, re.I)
    if match:
        return match.group(1).strip()[:2200]
    return text[:1500]


def guess_source(filename: str, first_page_text: str) -> str:
    """猜测论文来源。"""
    if "arxiv" in first_page_text.lower() or "arxiv" in filename.lower():
        return "arXiv"
    return ""


# ── 内容生成 ───────────────────────────────────────────────


def build_catalog_content(payload: Dict[str, Any]) -> str:
    """当没有完整 PDF 正文时，基于元信息生成扩展阅读稿。"""
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


def ensure_reader_content(paper: Dict[str, Any]) -> Dict[str, Any]:
    """确保论文有足够的阅读内容，不足时用扩展阅读稿补充。"""
    content = (paper.get("content") or "").strip()
    if len(content) >= 1500:
        return paper
    fallback = build_catalog_content(
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


# ── 检索相关 ───────────────────────────────────────────────


def rank_catalog(topic: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """根据主题和关键词对内置目录排序。"""
    query_text = f"{topic} {' '.join(keywords)}".lower()
    query_tokens = tokenize(query_text)
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


def build_search_links(topic: str) -> Dict[str, str]:
    """生成外部检索平台的链接。"""
    encoded = quote_plus(topic)
    return {
        "cnki": f"https://kns.cnki.net/kns8s/defaultresult/index?kw={encoded}",
        "arxiv": f"https://arxiv.org/search/?query={encoded}&searchtype=all",
        "semantic_scholar": f"https://www.semanticscholar.org/search?q={encoded}",
        "google_scholar": f"https://scholar.google.com/scholar?q={encoded}",
    }


def fallback_search_guide(topic: str) -> Dict[str, Any]:
    """当 LLM 不可用时，基于关键词拆解生成检索引导。"""
    raw_tokens = re.split(r"[^a-zA-Z0-9一-鿿]+", topic.lower())
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


# ── 上下文构建（供写作服务使用） ────────────────────────────


def paper_context(papers: List[Dict[str, Any]]) -> str:
    """将论文列表格式化为写作提示上下文。"""
    chunks = []
    for paper in papers:
        chunks.append(
            f"- {paper['title']} ({paper.get('year', '')})\n"
            f"  Summary: {paper.get('analysis', {}).get('summary', paper.get('abstract', '')[:220])}\n"
            f"  Problem: {paper.get('analysis', {}).get('research_problem', '')}\n"
            f"  Method: {paper.get('analysis', {}).get('method', '')}"
        )
    return "\n".join(chunks) or "No papers selected."


def notes_context(notes: List[Dict[str, Any]]) -> str:
    """将笔记列表格式化为写作提示上下文。"""
    return "\n".join(f"- {item['title']}: {item['content'][:220]}" for item in notes[:8]) or "No notes yet."
