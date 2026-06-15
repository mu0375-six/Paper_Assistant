"""检索与发现服务 Mixin。

包含论文检索、历史恢复、翻译候选、检索结果导入等逻辑。
依赖 self.store 和 self.llm_client（由 ScholarService 设置）。
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import requests

from .constants import (
    ARXIV_API_URL,
    CHINESE_TO_ENGLISH_KEYWORDS,
    SEARCH_PROMPT,
)
from .helpers import (
    build_catalog_content,
    build_search_links,
    fallback_search_guide,
    now,
    rank_catalog,
    safe_filename,
    tokenize,
)


# ── 中文→英文查询转换 ──────────────────────────────────────


def translate_chinese_query(query: str) -> str:
    """把中文搜索词翻译成英文关键词，以便 arXiv API 能匹配到结果。

    策略：逐个匹配中文关键词映射表，将匹配到的中文替换为英文；
    原有的英文词保留不变；最后拼接成英文搜索串。
    """
    result_parts = []
    remaining = query

    # 按长度降序排列，优先匹配较长的中文词组
    sorted_keys = sorted(CHINESE_TO_ENGLISH_KEYWORDS.keys(), key=len, reverse=True)
    matched_positions = []

    for cn_key in sorted_keys:
        start = 0
        while True:
            idx = remaining.find(cn_key, start)
            if idx == -1:
                break
            # 检查这个位置是否已经被更长的词覆盖
            overlap = False
            for m_start, m_end in matched_positions:
                if idx < m_end and idx + len(cn_key) > m_start:
                    overlap = True
                    break
            if not overlap:
                matched_positions.append((idx, idx + len(cn_key)))
                result_parts.append((idx, CHINESE_TO_ENGLISH_KEYWORDS[cn_key]))
            start = idx + len(cn_key)

    # 收集未被匹配的英文词
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", remaining)
    for word in words:
        result_parts.append((-1, word))

    if not result_parts:
        # 完全没有匹配，把原文直接传给 arXiv
        return query

    # 按位置排序后拼接，英文词追加在后面
    positioned = [p for p in result_parts if p[0] >= 0]
    positioned.sort(key=lambda x: x[0])
    english_parts = [p[1] for p in positioned] + [p[1] for p in result_parts if p[0] < 0]

    # 去重并拼接
    seen = set()
    unique = []
    for part in english_parts:
        for token in part.split():
            token_lower = token.lower()
            if token_lower not in seen:
                seen.add(token_lower)
                unique.append(token)

    return " ".join(unique) if unique else query


def search_arxiv(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """从 arXiv API 检索真实论文，返回标准化结果列表。

    arXiv API 无需 API Key，使用 HTTP GET 请求即可。
    返回的每个条目包含 title、authors、year、source、abstract、pdf_url 等字段。
    如果请求失败或解析出错，返回空列表。
    """
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    try:
        response = requests.get(ARXIV_API_URL, params=params, timeout=30)
        response.raise_for_status()
    except Exception:
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(response.text)
    except ET.ParseError:
        return []

    results = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        if title_el is None or summary_el is None:
            continue

        title = " ".join(title_el.text.split()).strip()
        abstract = " ".join(summary_el.text.split()).strip()
        year = ""
        if published_el is not None and published_el.text:
            year = published_el.text[:4]

        authors = []
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())
        authors_str = "; ".join(authors)

        pdf_url = ""
        text_url = ""
        for link_el in entry.findall("atom:link", ns):
            if link_el.get("title") == "pdf":
                pdf_url = link_el.get("href", "")
            elif link_el.get("type") == "text/html":
                text_url = link_el.get("href", "")

        # 如果没有显式 pdf 链接，尝试从 id 构造
        id_el = entry.find("atom:id", ns)
        if not pdf_url and id_el is not None and id_el.text:
            arxiv_id = id_el.text.split("/abs/")[-1]
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            if not text_url:
                text_url = id_el.text

        # 从摘要中提取关键词（取前几个有意义的词）
        keyword_tokens = re.findall(r"[a-zA-Z]{3,}", abstract.lower())
        seen = set()
        keywords = []
        for token in keyword_tokens:
            if token not in seen and token not in {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "has", "have", "this", "that", "with", "from", "they", "been", "said", "each", "which", "their", "will", "other", "about", "many", "then", "them", "these", "some", "would", "make", "like", "into", "time", "very", "when", "come", "could", "more", "over", "such", "after", "also", "than"}:
                seen.add(token)
                keywords.append(token)
                if len(keywords) >= 5:
                    break

        results.append({
            "title": title,
            "authors": authors_str,
            "year": year,
            "source": "arXiv",
            "keywords": keywords,
            "abstract": abstract,
            "excerpt": abstract[:300] + ("..." if len(abstract) > 300 else ""),
            "pdf_url": pdf_url,
            "text_url": text_url,
            "source_type": "open-access",
        })

    return results


# ── Mixin 类 ───────────────────────────────────────────────


class DiscoveryMixin:
    """检索与发现相关的方法。

    需要 self.store (JsonStore) 和 self.llm_client (DeepSeekClient)。
    """

    def search_topic(self, topic: str) -> Dict[str, Any]:
        topic = topic.strip()
        guide = self._build_search_guide(topic)
        keywords = guide["keywords"]

        # 优先从 arXiv API 检索真实论文
        # 中文搜索词需要先转成英文，否则 arXiv 匹配不到
        arxiv_query = translate_chinese_query(topic)
        arxiv_results = search_arxiv(arxiv_query, max_results=15)
        if arxiv_results:
            results = arxiv_results
        else:
            # arXiv 请求失败时回退到内置目录
            results = rank_catalog(topic, keywords)

        history_entry = self.store.save_search_history(
            {
                "query": topic,
                "keywords": keywords,
                "focus": guide["focus"],
                "screening_tips": guide["screening_tips"],
                "results_count": len(results),
                "top_titles": [item["title"] for item in results[:5]],
                "created_at": now(),
            }
        )
        return {
            "query": topic,
            "keywords": keywords,
            "focus": guide["focus"],
            "screening_tips": guide["screening_tips"],
            "results": results[:10],
            "history_id": history_entry["id"],
            "search_links": build_search_links(topic),
        }

    def restore_search_history(self, history_id: str) -> Dict[str, Any]:
        history = next((item for item in self.store.list_search_history() if item.get("id") == history_id), None)
        if not history:
            raise ValueError("Search history not found.")
        topic = (history.get("query") or "").strip()
        keywords = [item for item in history.get("keywords", []) if str(item).strip()] or fallback_search_guide(topic)["keywords"]

        # 优先从 arXiv API 检索
        arxiv_query = translate_chinese_query(topic)
        arxiv_results = search_arxiv(arxiv_query, max_results=15)
        if arxiv_results:
            results = arxiv_results
        else:
            results = rank_catalog(topic, keywords)

        return {
            "query": topic,
            "keywords": keywords,
            "focus": history.get("focus") or fallback_search_guide(topic)["focus"],
            "screening_tips": history.get("screening_tips") or fallback_search_guide(topic)["screening_tips"],
            "results": results[:10],
            "history_id": history.get("id"),
            "search_links": build_search_links(topic),
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
            paper_payload["content"] = build_catalog_content(payload)
        return self.create_paper(paper_payload)

    def download_external_pdf(self, pdf_url: str, title: str) -> Dict[str, Any]:
        if not pdf_url:
            raise ValueError("pdf_url is required")
        filename = safe_filename(title or "paper") + ".pdf"
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

    # ── 内部方法 ───────────────────────────────────────────

    def _build_search_guide(self, topic: str) -> Dict[str, Any]:
        fb = fallback_search_guide(topic)
        if self.llm_client.is_configured():
            try:
                result, _usage = self.llm_client.chat_json_with_usage(SEARCH_PROMPT, topic)
                keywords = [item.strip() for item in result.get("keywords", []) if str(item).strip()]
                if keywords:
                    return {
                        "keywords": keywords[:6],
                        "focus": (result.get("focus") or fb["focus"]).strip(),
                        "screening_tips": result.get("screening_tips") or fb["screening_tips"],
                    }
            except Exception:
                pass
        return fb
