"""FastAPI 路由注册。

使用 FastAPI 替代 Flask，提供：
- 自动生成的 Swagger UI（/docs）
- Pydantic 请求模型自动校验
- 统一的异常处理
- 类型标注的响应格式
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .deepseek_client import DeepSeekClient
from .schemas import (
    AssistantChatRequest,
    CreatePaperRequest,
    DownloadPdfRequest,
    ResearchPlanRequest,
    SaveDiscoveryResultRequest,
    SaveNoteRequest,
    SearchRequest,
    SentenceSearchRequest,
    SubmitChallengeAnswerRequest,
    TranslatePaperRequest,
    TranslateResultRequest,
    WritingPackRequest,
)
from .scholar_service import ScholarService
from .storage import JsonStore


BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"


def create_router(store: JsonStore, llm_client: DeepSeekClient, scholar: ScholarService) -> APIRouter:
    router = APIRouter()

    # ── 页面路由 ────────────────────────────────────────────

    @router.get("/")
    def home():
        return FileResponse(WEB_DIR / "home.html")

    @router.get("/discovery")
    def discovery_page():
        return FileResponse(WEB_DIR / "discovery.html")

    @router.get("/reader")
    def reader_page():
        return FileResponse(WEB_DIR / "reader.html")

    @router.get("/workspace")
    def workspace_page():
        return FileResponse(WEB_DIR / "workspace.html")

    @router.get("/downloads/{filename:path}")
    def download_file(filename: str):
        return FileResponse(store.downloads_dir / filename)

    # ── 状态与仪表盘 ────────────────────────────────────────

    @router.get("/api/status")
    def status():
        return {"configured": llm_client.is_configured(), "model": llm_client.model, **store.stats()}

    @router.get("/api/dashboard")
    def dashboard():
        return scholar.dashboard()

    # ── 论文 CRUD ────────────────────────────────────────────

    @router.get("/api/papers/{paper_id}")
    def get_paper(paper_id: str):
        try:
            return scholar.get_paper(paper_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Paper not found.")

    @router.post("/api/papers")
    def create_paper(body: CreatePaperRequest):
        return scholar.create_paper(body.model_dump())

    @router.post("/api/tutorial/sample-paper")
    def tutorial_sample_paper():
        return scholar.ensure_sample_paper()

    @router.post("/api/papers/import-pdf")
    async def import_pdf(file: UploadFile):
        if not file.filename:
            raise HTTPException(status_code=400, detail="PDF file is required")
        try:
            return scholar.import_pdf(file)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF import failed: {exc}")

    # ── AI 精读与翻译 ────────────────────────────────────────

    @router.post("/api/papers/{paper_id}/analyze")
    def analyze_paper(paper_id: str):
        try:
            return scholar.analyze_paper(paper_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Paper not found.")

    @router.post("/api/papers/{paper_id}/translate")
    def translate_paper(paper_id: str, body: TranslatePaperRequest):
        try:
            return scholar.translate_paper(paper_id, body.target_language, body.scope)
        except ValueError:
            raise HTTPException(status_code=404, detail="Paper not found.")

    @router.post("/api/papers/{paper_id}/sentence-search")
    def sentence_search(paper_id: str, body: SentenceSearchRequest):
        try:
            return scholar.sentence_search(paper_id, body.query)
        except ValueError:
            raise HTTPException(status_code=404, detail="Paper not found.")

    @router.post("/api/papers/{paper_id}/assistant")
    def assistant_chat(paper_id: str, body: AssistantChatRequest):
        try:
            return scholar.assistant_chat(paper_id, body.message)
        except ValueError:
            raise HTTPException(status_code=404, detail="Paper not found.")

    # ── 闯关训练 ─────────────────────────────────────────────

    @router.get("/api/papers/{paper_id}/challenge")
    def get_challenge(paper_id: str):
        try:
            return scholar.get_challenge(paper_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Paper not found.")

    @router.post("/api/papers/{paper_id}/challenge/{stage_id}")
    def submit_challenge_answer(paper_id: str, stage_id: str, body: SubmitChallengeAnswerRequest):
        try:
            return scholar.submit_challenge_answer(paper_id, stage_id, body.answer)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.get("/api/papers/{paper_id}/challenge-report")
    def challenge_report(paper_id: str):
        try:
            return scholar.challenge_report(paper_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Paper not found.")

    # ── 笔记 ─────────────────────────────────────────────────

    @router.post("/api/notes")
    def save_note(body: SaveNoteRequest):
        return scholar.save_note(body.model_dump())

    # ── 检索与发现 ───────────────────────────────────────────

    @router.post("/api/discovery/search")
    def discovery_search(body: SearchRequest):
        return scholar.search_topic(body.topic)

    @router.get("/api/discovery/history/{history_id}")
    def restore_discovery_history(history_id: str):
        try:
            return scholar.restore_search_history(history_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Search history not found.")

    @router.post("/api/discovery/translate-result")
    def translate_result(body: TranslateResultRequest):
        return scholar.translate_candidate(body.model_dump(), body.target_language)

    @router.post("/api/discovery/download-pdf")
    def download_pdf(body: DownloadPdfRequest):
        try:
            return scholar.download_external_pdf(body.pdf_url, body.title)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @router.post("/api/discovery/save-result")
    def save_discovery_result(body: SaveDiscoveryResultRequest):
        return scholar.import_catalog_result(body.model_dump())

    # ── 研究计划与写作包 ─────────────────────────────────────

    @router.post("/api/research-plan")
    def research_plan(body: ResearchPlanRequest):
        return scholar.build_research_plan(body.topic, body.paper_ids)

    @router.post("/api/writing-pack")
    def writing_pack(body: WritingPackRequest):
        return scholar.generate_writing_pack(body.topic, body.paper_ids, body.goal)

    return router
