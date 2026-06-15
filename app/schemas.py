"""Pydantic 请求/响应模型。

用于 FastAPI 路由的请求体验证和响应类型标注，
替代原来手写的 payload.get("xxx") or "").strip() 校验。

Pydantic 自动完成：
- 必填字段缺失 → 422
- 类型不匹配 → 422
- RequiredStr 纯空格 → 422（strip 后 min_length=1 不满足）
"""

from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field, StringConstraints

# 必填非空字符串：自动 strip 后校验长度 >= 1，纯空格也会被拒绝
RequiredStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# ── 通用响应 ───────────────────────────────────────────────


class ErrorResponse(BaseModel):
    error: str


# ── 检索相关 ───────────────────────────────────────────────


class SearchRequest(BaseModel):
    topic: RequiredStr = Field(description="检索主题关键词")


class TranslateResultRequest(BaseModel):
    title: str = ""
    authors: str = ""
    year: str = ""
    source: str = ""
    abstract: str = ""
    excerpt: str = ""
    pdf_url: str = ""
    text_url: str = ""
    target_language: str = "zh"


class DownloadPdfRequest(BaseModel):
    pdf_url: RequiredStr = Field(description="PDF 下载链接")
    title: str = "paper"


class SaveDiscoveryResultRequest(BaseModel):
    title: RequiredStr = Field(description="论文标题")
    authors: str = ""
    year: str = ""
    source: str = ""
    abstract: str = ""
    excerpt: str = ""
    pdf_url: str = ""
    text_url: str = ""


# ── 论文相关 ───────────────────────────────────────────────


class CreatePaperRequest(BaseModel):
    id: str = ""
    title: RequiredStr = Field(description="论文标题")
    authors: str = ""
    year: str = ""
    source: str = ""
    abstract: str = ""
    content: str = ""
    pages: List[str] = []
    figures: List[Dict[str, Any]] = []
    pdf_url: str = ""
    text_url: str = ""
    analysis: Dict[str, Any] = {}


class TranslatePaperRequest(BaseModel):
    target_language: str = "zh"
    scope: str = "abstract"


class SentenceSearchRequest(BaseModel):
    query: RequiredStr = Field(description="检索关键词")


class AssistantChatRequest(BaseModel):
    message: RequiredStr = Field(description="用户提问")


# ── 笔记相关 ───────────────────────────────────────────────


class SaveNoteRequest(BaseModel):
    id: str = ""
    paper_id: RequiredStr = Field(description="关联论文 ID")
    title: str = ""
    content: str = ""
    kind: str = "manual"
    source_text: str = ""
    page_label: str = ""
    anchor_text: str = ""
    ai_prompt: str = ""
    assistant_message_id: str = ""


# ── 闯关相关 ───────────────────────────────────────────────


class SubmitChallengeAnswerRequest(BaseModel):
    answer: RequiredStr = Field(description="闯关答案")


# ── 研究计划 / 写作包 ─────────────────────────────────────


class ResearchPlanRequest(BaseModel):
    topic: RequiredStr = Field(description="研究主题")
    paper_ids: List[str] = []


class WritingPackRequest(BaseModel):
    topic: RequiredStr = Field(description="写作主题")
    goal: str = ""
    paper_ids: List[str] = []
