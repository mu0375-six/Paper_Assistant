from pathlib import Path

from flask import jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .deepseek_client import DeepSeekClient
from .scholar_service import ScholarService
from .storage import JsonStore


BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"


def register_routes(app):
    store = JsonStore(DATA_DIR)
    llm_client = DeepSeekClient()
    scholar = ScholarService(store, llm_client)

    @app.errorhandler(Exception)
    def handle_api_error(exc):
        if not request.path.startswith("/api/"):
            raise exc
        if isinstance(exc, HTTPException):
            return jsonify({"error": exc.description or exc.name}), exc.code or 500
        return jsonify({"error": f"{exc.__class__.__name__}: {exc}"}), 500

    def render_page(name: str):
        return send_from_directory(WEB_DIR, name)

    @app.get("/")
    def home():
        return render_page("home.html")

    @app.get("/discovery")
    def discovery_page():
        return render_page("discovery.html")

    @app.get("/reader")
    def reader_page():
        return render_page("reader.html")

    @app.get("/workspace")
    def workspace_page():
        return render_page("workspace.html")

    @app.get("/downloads/<path:filename>")
    def download_file(filename: str):
        return send_from_directory(store.downloads_dir, filename)

    @app.get("/api/status")
    def status():
        return jsonify({"configured": llm_client.is_configured(), "model": llm_client.model, **store.stats()})

    @app.get("/api/dashboard")
    def dashboard():
        return jsonify(scholar.dashboard())

    @app.get("/api/papers/<paper_id>")
    def get_paper(paper_id: str):
        try:
            return jsonify(scholar.get_paper(paper_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/discovery/search")
    def discovery_search():
        payload = request.get_json(force=True)
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return jsonify({"error": "topic is required"}), 400
        return jsonify(scholar.search_topic(topic))

    @app.get("/api/discovery/history/<history_id>")
    def restore_discovery_history(history_id: str):
        try:
            return jsonify(scholar.restore_search_history(history_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/discovery/translate-result")
    def translate_result():
        payload = request.get_json(force=True)
        return jsonify(scholar.translate_candidate(payload, (payload.get("target_language") or "zh").strip()))

    @app.post("/api/discovery/download-pdf")
    def download_pdf():
        payload = request.get_json(force=True)
        pdf_url = (payload.get("pdf_url") or "").strip()
        if not pdf_url:
            return jsonify({"error": "pdf_url is required"}), 400
        try:
            return jsonify(scholar.download_external_pdf(pdf_url, (payload.get("title") or "paper").strip()))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.post("/api/discovery/save-result")
    def save_discovery_result():
        payload = request.get_json(force=True)
        title = (payload.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        return jsonify(scholar.import_catalog_result(payload))

    @app.post("/api/papers/import-pdf")
    def import_pdf():
        pdf_file = request.files.get("file")
        if not pdf_file or not pdf_file.filename:
            return jsonify({"error": "PDF file is required"}), 400
        try:
            return jsonify(scholar.import_pdf(pdf_file))
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 500
        except Exception as exc:
            return jsonify({"error": f"PDF import failed: {exc}"}), 500

    @app.post("/api/papers")
    def create_paper():
        payload = request.get_json(force=True)
        title = (payload.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        return jsonify(scholar.create_paper(payload))

    @app.post("/api/tutorial/sample-paper")
    def tutorial_sample_paper():
        return jsonify(scholar.ensure_sample_paper())

    @app.post("/api/papers/<paper_id>/analyze")
    def analyze_paper(paper_id: str):
        try:
            return jsonify(scholar.analyze_paper(paper_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/papers/<paper_id>/translate")
    def translate_paper(paper_id: str):
        payload = request.get_json(force=True)
        return jsonify(
            scholar.translate_paper(
                paper_id,
                (payload.get("target_language") or "zh").strip(),
                (payload.get("scope") or "abstract").strip(),
            )
        )

    @app.post("/api/papers/<paper_id>/sentence-search")
    def sentence_search(paper_id: str):
        payload = request.get_json(force=True)
        query = (payload.get("query") or "").strip()
        if not query:
            return jsonify({"error": "query is required"}), 400
        return jsonify(scholar.sentence_search(paper_id, query))

    @app.post("/api/papers/<paper_id>/assistant")
    def assistant_chat(paper_id: str):
        payload = request.get_json(force=True)
        message = (payload.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message is required"}), 400
        return jsonify(scholar.assistant_chat(paper_id, message))

    @app.get("/api/papers/<paper_id>/challenge")
    def get_challenge(paper_id: str):
        try:
            return jsonify(scholar.get_challenge(paper_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/papers/<paper_id>/challenge/<stage_id>")
    def submit_challenge_answer(paper_id: str, stage_id: str):
        payload = request.get_json(force=True)
        answer = (payload.get("answer") or "").strip()
        if not answer:
            return jsonify({"error": "answer is required"}), 400
        try:
            return jsonify(scholar.submit_challenge_answer(paper_id, stage_id, answer))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.get("/api/papers/<paper_id>/challenge-report")
    def challenge_report(paper_id: str):
        try:
            return jsonify(scholar.challenge_report(paper_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/notes")
    def save_note():
        payload = request.get_json(force=True)
        paper_id = (payload.get("paper_id") or "").strip()
        if not paper_id:
            return jsonify({"error": "paper_id is required"}), 400
        return jsonify(scholar.save_note(payload))

    @app.post("/api/research-plan")
    def research_plan():
        payload = request.get_json(force=True)
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return jsonify({"error": "topic is required"}), 400
        selected_ids = payload.get("paper_ids") or []
        return jsonify(scholar.build_research_plan(topic, selected_ids))

    @app.post("/api/writing-pack")
    def writing_pack():
        payload = request.get_json(force=True)
        topic = (payload.get("topic") or "").strip()
        goal = (payload.get("goal") or "").strip()
        if not topic:
            return jsonify({"error": "topic is required"}), 400
        selected_ids = payload.get("paper_ids") or []
        return jsonify(scholar.generate_writing_pack(topic, selected_ids, goal))
