(() => {
  const state = {
    dashboard: { papers: [], assistant_messages: [] },
    challenge: null,
    report: null,
    retryingStageId: "",
    tutorialOpen: false,
    selectedPaperId: new URLSearchParams(window.location.search).get("paper") || localStorage.getItem("scholarflow.selectedPaperId") || "",
  };

  const $ = (selector) => document.querySelector(selector);
  const readerPanel = $("#readerPanel");
  const paperList = $("#readerPaperList");
  const feedback = $("#readerFeedback");
  const tutorialPanel = $("#tutorialPanel");
  const tutorialModal = $("#tutorialModal");
  const tutorialModalBody = $("#tutorialModalBody");
  const analysisPanel = $("#analysisPanel");
  const annotationPanel = $("#annotationPanel");
  const challengePanel = $("#challengePanel");
  const readerNotesPanel = $("#readerNotesPanel");
  const messagesPanel = $("#assistantMessagesPanel");
  const assistantForm = $("#assistantForm");
  const assistantInput = $("#assistantInput");
  const aiRail = $(".ai-rail");
  const selectionMenu = $("#selectionMenu");
  const selectionDock = $("#selectionDock");
  const selectionDockText = $("#selectionDockText");
  let selectionMenuTimer = 0;
  let clipboardSelectionText = "";

  const tutorialSteps = [
    { title: "1. 先看题名、摘要、关键词", body: "先判断论文研究对象、场景和核心概念，不急着逐字读正文。" },
    { title: "2. 找引言末尾的研究问题", body: "重点找“已有研究不足”“本文提出”“本文贡献”，用自己的话写出痛点。" },
    { title: "3. 拆方法流程", body: "用“输入数据 → 处理步骤 → 输出结果”复述方法，避免只背术语。" },
    { title: "4. 看图表和实验", body: "每张关键图表都问两句：它证明了什么？它不能证明什么？" },
    { title: "5. 追问局限", body: "从数据、假设、实验范围和应用场景里找边界，这一步最能体现理解深度。" },
    { title: "6. 形成笔记和汇报", body: "把 AI 问答、闯关反馈和选区笔记整理成课堂汇报，而不是停留在摘要。" },
  ];

  const buttonHelp = {
    tutorialButton: "打开新手教程，查看 6 步论文阅读路线和按钮说明。",
    analyzeButton: "让 AI 根据当前论文生成摘要、关键词、研究问题和推荐追问。",
    summaryButton: "切换到右侧“摘要”面板，查看当前论文的结构化理解。",
    selectionModeButton: "打开文本选择层。选中文字后可以解释、翻译、高亮、记笔记或提问。",
    clipboardSelectionButton: "处理原生 PDF 中复制出来的文字，适合 PDF 无法直接弹出选区菜单时使用。",
    openPdfButton: "在新标签页打开当前论文 PDF 原文。",
    samplePaperButton: "导入内置示例论文，适合第一次体验完整阅读流程。",
    attachButton: "提示：AI 问答会自动附带当前论文上下文。",
    aiModeButton: "当前为论文精读问答模式。",
    assistantSendButton: "发送问题给 AI 助手。",
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function scoreTone(score) {
    const value = Number(score) || 0;
    if (value >= 80) return "is-strong";
    if (value >= 60) return "is-pass";
    return "is-low";
  }

  function challengeLevelLabel(level) {
    const normalized = String(level || "").toLowerCase();
    const labels = {
      strong: "优秀",
      pass: "通过",
      revise: "待完善",
      needs_work: "需要重做",
      fail: "需要重做",
    };
    return labels[normalized] || "AI 反馈";
  }

  function applyButtonHelp() {
    Object.entries(buttonHelp).forEach(([id, help]) => {
      const element = document.getElementById(id);
      if (element) {
        element.title = help;
        element.setAttribute("aria-label", element.getAttribute("aria-label") || help);
      }
    });
    document.querySelectorAll("[data-ai-pane]").forEach((button) => {
      const labels = {
        tutorial: "教程：查看论文阅读路线、按钮说明和新手任务。",
        summary: "摘要：查看 AI 精读后的论文摘要、关键词和推荐追问。",
        annotations: "标注：查看从 PDF 选区保存的解释、翻译和笔记。",
        challenge: "闯关：回答 5 个精读问题，获得 AI 纠错和评分。",
        chat: "AI 问答：围绕当前论文连续提问。",
        notes: "笔记：查看本篇论文已保存的阅读记录。",
      };
      button.title = labels[button.dataset.aiPane] || "切换右侧面板";
    });
    document.querySelectorAll("[data-selection-action], [data-dock-action]").forEach((button) => {
      const labels = {
        explain: "解释选中文字的含义。",
        translate: "把选中文字翻译成中文或更易懂的表达。",
        highlight: "把选中文字高亮，方便回看。",
        note: "把选中文字保存为阅读笔记。",
        ask: "把选中文字放入 AI 问答框继续追问。",
      };
      const action = button.dataset.selectionAction || button.dataset.dockAction;
      button.title = labels[action] || "处理选中文字";
    });
    document.querySelectorAll("[data-retry-challenge]").forEach((button) => {
      button.title = button.textContent.includes("重新") ? "重新打开本关答题框，覆盖上一轮答案。" : "打开这一关的答题框。";
    });
  }

  function setFeedback(message, type = "") {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.className = `reader-feedback ${type ? `is-${type}` : ""}`;
  }

  function setAiPane(pane) {
    const allowed = ["tutorial", "summary", "annotations", "challenge", "chat", "notes"];
    const nextPane = allowed.includes(pane) ? pane : "chat";
    if (aiRail) {
      aiRail.classList.toggle("is-tutorial", nextPane === "tutorial");
      aiRail.classList.toggle("is-summary", nextPane === "summary");
      aiRail.classList.toggle("is-annotations", nextPane === "annotations");
      aiRail.classList.toggle("is-challenge", nextPane === "challenge");
      aiRail.classList.toggle("is-chat", nextPane === "chat");
      aiRail.classList.toggle("is-notes", nextPane === "notes");
    }
    document.querySelectorAll("[data-ai-pane]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.aiPane === nextPane);
    });
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const raw = await response.text();
    let data = {};
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch {
      data = { error: raw.slice(0, 240) || "服务器没有返回 JSON 错误信息。" };
    }
    if (!response.ok) throw new Error(data.error || `请求失败：HTTP ${response.status}`);
    return data;
  }

  function cleanedBodyText(paper) {
    return compactText(allText(paper))
      .replace(/(摘要|关键词|中图分类号|文献标识码|文章编号)\s*[:：]/g, "\n$1：")
      .replace(/(引言|结论|参考文献|References?|Abstract|Keywords?)\s*[:：]?/gi, "\n$1\n")
      .replace(/([。！？；])\s*/g, "$1\n")
      .split(/\n+/)
      .map((item) => item.trim())
      .filter((item) => item.length > 12)
      .slice(0, 120);
  }

  function selectionParagraphsFromText(text) {
    return compactText(text)
      .replace(/(摘要|关键词|中图分类号|文献标识码|文章编号)\s*[:：]/g, "\n$1：")
      .replace(/(引言|结论|参考文献|References?|Abstract|Keywords?)\s*[:：]?/gi, "\n$1\n")
      .replace(/([。！？；])\s*/g, "$1\n")
      .split(/\n+/)
      .map((item) => item.trim())
      .filter((item) => item.length > 12)
      .slice(0, 70);
  }

  function renderSelectionTextLayer(paper) {
    const pages = Array.isArray(paper?.pages) ? paper.pages.filter(Boolean) : [];
    if (pages.length) {
      return pages.map((pageText, index) => {
        const paragraphs = selectionParagraphsFromText(pageText);
        return `
          <section class="selection-page" data-page-label="第 ${index + 1} 页">
            <h3>第 ${index + 1} 页</h3>
            ${paragraphs.length ? paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("") : "<p>这一页暂未抽取到可选中文本。</p>"}
          </section>
        `;
      }).join("");
    }
    const paragraphs = cleanedBodyText(paper);
    return paragraphs.length
      ? `<section class="selection-page" data-page-label="全文文本">${paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}</section>`
      : '<section class="selection-page" data-page-label="无文本"><p>当前论文暂未抽取到可选择文本。你仍然可以阅读 PDF 原貌，或重新上传更清晰的 PDF。</p></section>';
  }

  function pdfUrl(paper) {
    return paper?.downloaded_pdf_url || paper?.pdf_url || "";
  }

  function selectedPaper() {
    const papers = state.dashboard.papers || [];
    return papers.find((paper) => paper.id === state.selectedPaperId) || papers[0] || null;
  }

  function allText(paper) {
    return [paper?.abstract || "", paper?.content || "", ...(Array.isArray(paper?.pages) ? paper.pages : [])].filter(Boolean).join("\n");
  }

  function compactText(text) {
    return String(text || "").replace(/\s+/g, " ").trim();
  }

  function splitKeywords(text) {
    return String(text || "")
      .split(/[;；,，、]/)
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 12);
  }

  function extractKeywords(paper) {
    if (Array.isArray(paper?.analysis?.keywords) && paper.analysis.keywords.length) return paper.analysis.keywords.slice(0, 12);
    const text = compactText(allText(paper));
    const match = text.match(/(?:关键词|关键\s*词|Keywords?|Key\s*words?)\s*[:：]\s*([\s\S]{2,260}?)(?=中图分类号|文献标识码|文章编号|Abstract|参考文献|References?|$)/i);
    return match ? splitKeywords(match[1]) : [];
  }

  function extractEnglishAbstract(paper) {
    const text = compactText(allText(paper));
    const match = text.match(/(?:Abstract|ABSTRACT)\s*[:：]?\s*([\s\S]{40,1800}?)(?=Keywords?|Key\s*words?|References?|参考文献|$)/);
    return match ? match[1].trim() : "";
  }

  function extractReferences(paper) {
    const text = compactText(allText(paper));
    const match = text.match(/(?:参考文献|References?)\s*[:：]?\s*([\s\S]{20,6000})$/i);
    if (!match) return [];
    return match[1]
      .split(/\s*(?=\[\s*\d+\s*\]|\d+\.\s+)/)
      .map((item) => item.trim())
      .filter((item) => item.length > 8)
      .slice(0, 18);
  }

  function normalizeSelection() {
    const paper = selectedPaper();
    if (paper && paper.id !== state.selectedPaperId) {
      state.selectedPaperId = paper.id;
      localStorage.setItem("scholarflow.selectedPaperId", paper.id);
    }
    return paper;
  }

  function renderPaperList() {
    if (!paperList) return;
    const papers = state.dashboard.papers || [];
    paperList.innerHTML = papers.length
      ? papers.map((paper) => `
          <button class="paper-item ${paper.id === state.selectedPaperId ? "is-active" : ""}" type="button" data-paper-id="${escapeHtml(paper.id)}">
            <strong>${escapeHtml(paper.title || "未命名论文")}</strong>
            <span>${pdfUrl(paper) ? "PDF 已保存" : "缺少 PDF"} · ${escapeHtml(paper.year || "年份待补充")}</span>
          </button>
        `).join("")
      : '<p class="empty-state">还没有文献。请先上传 PDF。</p>';

    paperList.querySelectorAll("[data-paper-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedPaperId = button.dataset.paperId;
        state.challenge = null;
        state.report = null;
        state.retryingStageId = "";
        localStorage.setItem("scholarflow.selectedPaperId", state.selectedPaperId);
        renderAll();
      });
    });
  }

  function renderReader() {
    const paper = normalizeSelection();
    const title = paper?.title || "请选择一篇文献";
    const url = pdfUrl(paper);
    $("#activePaperTitle").textContent = title;
    $("#readerPageIndicator").textContent = url ? "PDF" : "缺失";
    $("#pdfStatusBadge").textContent = url ? "PDF 原貌渲染" : "等待上传 PDF";
    $("#pdfStatusBadge").classList.toggle("is-missing", !url);

    const openButton = $("#openPdfButton");
    if (openButton) {
      openButton.href = url || "#";
      openButton.classList.toggle("is-unavailable", !url);
      openButton.textContent = url ? "打开 PDF" : "PDF 缺失";
      openButton.onclick = url ? null : (event) => {
        event.preventDefault();
        setFeedback("当前文献没有保存原始 PDF，请从左侧重新上传。", "error");
      };
    }

    if (!paper) {
      readerPanel.className = "pdf-canvas empty-state";
      readerPanel.textContent = "从左侧选择或上传 PDF 后，这里会直接显示原始 PDF 正文。";
      return;
    }

    if (!url) {
      if (allText(paper)) {
        readerPanel.className = "pdf-canvas tutorial-text-reader";
        readerPanel.innerHTML = `
          <div class="selection-layer-head">
            <strong>示例文本阅读视图</strong>
            <span>这篇示例用于练习阅读路线；真实论文建议上传 PDF 查看原始版式。</span>
          </div>
          <div class="selection-paper-text">
            ${renderSelectionTextLayer(paper)}
          </div>
        `;
        bindSelectionLayer();
        return;
      }
      readerPanel.className = "pdf-canvas pdf-missing-state";
      readerPanel.innerHTML = `
        <h2>这篇文献还没有原始 PDF</h2>
        <p>当前记录只有抽取后的文字。要像 Moonlight 一样正确显示公式、图表和排版，需要保存原始 PDF。</p>
        <label class="primary-upload">
          上传这篇论文的 PDF
          <input id="inlinePdfInput" type="file" accept="application/pdf" hidden />
        </label>
      `;
      $("#inlinePdfInput")?.addEventListener("change", importPdf);
      return;
    }

    readerPanel.className = "pdf-canvas";
    readerPanel.innerHTML = `
      <iframe class="pdf-frame" src="${escapeHtml(url)}#toolbar=1&navpanes=0&view=FitH" title="${escapeHtml(title)}"></iframe>
      <div id="selectionTextLayer" class="selection-text-layer" hidden>
        <div class="selection-layer-head">
          <strong>文本选择层</strong>
          <span>选中文字后可解释、翻译、高亮或向 AI 提问。</span>
        </div>
        <div class="selection-paper-text">
          ${renderSelectionTextLayer(paper)}
        </div>
      </div>
    `;
    bindSelectionLayer();
    applySelectionMode();
  }

  function renderAnalysis() {
    const paper = selectedPaper();
    if (!analysisPanel) return;
    if (!paper) {
      analysisPanel.innerHTML = '<p class="empty-state">请选择一篇论文，然后点击“AI 精读”。</p>';
      return;
    }

    const keywords = extractKeywords(paper);
    const englishAbstract = extractEnglishAbstract(paper);
    const references = extractReferences(paper);
    const analysis = paper.analysis || {};
    const questions = (Array.isArray(analysis.reading_questions) && analysis.reading_questions.length
      ? analysis.reading_questions
      : ["这篇论文的核心问题是什么？", "方法的新意和边界分别是什么？", "有什么局限性？"]
    ).slice(0, 5);

    analysisPanel.innerHTML = `
      <div class="ai-tool-row">
        <span class="ai-tool">AI</span>
        <strong>论文助手</strong>
      </div>
      <article class="ai-context-card">
        <h3>当前上下文</h3>
        <p>${escapeHtml(analysis.summary || "点击“AI 精读”后，这里会提炼论文摘要，再进入下方连续问答。")}</p>
      </article>
      <div class="keyword-list ai-context-keywords">
        ${keywords.length ? keywords.slice(0, 4).map((item) => `<span class="keyword-chip">${escapeHtml(item)}</span>`).join("") : '<span class="missing-inline">未识别到关键词</span>'}
      </div>
      <div class="question-list ai-context-questions">
        ${questions.slice(0, 3).map((question) => `<button class="question-pill" type="button" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>`).join("")}
      </div>
      <details class="ai-context-more">
        <summary>英文摘要与参考文献</summary>
        <p>${escapeHtml(englishAbstract || "未识别到英文摘要。")}</p>
        ${references.length ? `<ol class="reference-list">${references.slice(0, 6).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>` : '<p class="missing-inline">未识别到参考文献，建议直接在 PDF 正文末尾查看。</p>'}
      </details>
    `;
    analysisPanel.querySelectorAll("[data-question]").forEach((button) => {
      button.addEventListener("click", () => {
        setAiPane("chat");
        assistantInput.value = button.dataset.question;
        assistantInput.focus();
      });
    });
  }

  function renderTutorialPanel() {
    if (!tutorialPanel) return;
    tutorialPanel.innerHTML = `
      <div class="ai-tool-row">
        <span class="ai-tool">?</span>
        <strong>新手教程</strong>
      </div>
      <article class="tutorial-card tutorial-card--focus">
        <h3>推荐路线：先读懂，再让 AI 帮你纠错</h3>
        <p>第一次使用时，建议先导入示例论文，按下面 6 步走一遍，再换成自己的 PDF。</p>
        <button class="challenge-primary" type="button" data-import-sample>导入示例论文</button>
      </article>
      <div class="tutorial-step-list">
        ${tutorialSteps.map((step) => `
          <article class="tutorial-step">
            <strong>${escapeHtml(step.title)}</strong>
            <p>${escapeHtml(step.body)}</p>
          </article>
        `).join("")}
      </div>
      <article class="tutorial-card">
        <h3>按钮说明</h3>
        <dl class="button-help-list">
          <div><dt>AI 精读</dt><dd>生成摘要、关键词、研究问题和追问。</dd></div>
          <div><dt>文本层选区</dt><dd>在可抽取文本上选中一句话，继续解释、翻译、提问或保存笔记。</dd></div>
          <div><dt>复制处理</dt><dd>用于原生 PDF 选中文字后粘贴处理。</dd></div>
          <div><dt>闯关</dt><dd>用 5 个问题训练论文精读能力，提交后得到纠错评分。</dd></div>
          <div><dt>AI 问答</dt><dd>围绕当前论文连续提问，适合追问概念、方法和局限。</dd></div>
          <div><dt>笔记</dt><dd>保存选区、AI 回答和你的阅读想法，后续用于写作。</dd></div>
        </dl>
      </article>
    `;
    tutorialPanel.querySelector("[data-import-sample]")?.addEventListener("click", importSamplePaper);
  }

  function renderMessages(extraMessages = []) {
    const paper = selectedPaper();
    if (!messagesPanel) return;
    if (!paper) {
      messagesPanel.innerHTML = '<p class="empty-state">先选择一篇论文，然后可以继续追问。</p>';
      return;
    }
    const saved = (state.dashboard.assistant_messages || []).filter((item) => item.paper_id === paper.id);
    const messages = [...saved, ...extraMessages].slice(-16);
    messagesPanel.innerHTML = messages.length
      ? messages.map((message) => `
          <article class="chat-message ${message.role === "user" ? "is-user" : "is-ai"}">
            <p><strong>${message.role === "user" ? "你" : "AI"}：</strong>${escapeHtml(message.content)}</p>
            ${message.role === "assistant" && message.id ? `<button class="message-save" type="button" data-save-message="${escapeHtml(message.id)}">保存为笔记</button>` : ""}
          </article>
        `).join("")
      : '<p class="empty-state">还没有对话记录。你可以直接开始问问题。</p>';
    messagesPanel.querySelectorAll("[data-save-message]").forEach((button) => {
      button.addEventListener("click", () => saveAssistantMessageAsNote(button.dataset.saveMessage));
    });
    messagesPanel.scrollTop = messagesPanel.scrollHeight;
  }

  function renderAnnotationPanel() {
    if (!annotationPanel) return;
    const paper = selectedPaper();
    if (!paper) {
      annotationPanel.innerHTML = '<p class="empty-state">请选择论文后再做标注。</p>';
      return;
    }
    const notes = (state.dashboard.notes || []).filter((note) => note.paper_id === paper.id && note.kind === "selection");
    annotationPanel.innerHTML = `
      <div class="ai-tool-row">
        <span class="ai-tool">摘</span>
        <strong>文本标注</strong>
      </div>
      <article class="ai-card">
        <h3>如何使用</h3>
        <p>点击顶部“文本层选区”，在可选中文本层里选中文字，就会出现解释、翻译、加入笔记和追问操作。原始 PDF 仍负责公式、图表和版式。</p>
      </article>
      <article class="ai-card">
        <h3>本篇标注</h3>
        ${notes.length ? notes.map((note) => renderNoteCard(note)).join("") : '<p class="missing-inline">还没有选区标注。课堂展示时可以先选中一段摘要并加入笔记。</p>'}
      </article>
    `;
  }

  function renderNotesPanel() {
    if (!readerNotesPanel) return;
    const paper = selectedPaper();
    if (!paper) {
      readerNotesPanel.innerHTML = '<p class="empty-state">请选择论文后查看笔记。</p>';
      return;
    }
    const notes = (state.dashboard.notes || []).filter((note) => note.paper_id === paper.id);
    readerNotesPanel.innerHTML = `
      <div class="ai-tool-row">
        <span class="ai-tool">记</span>
        <strong>阅读笔记</strong>
      </div>
      <article class="ai-card">
        <h3>${escapeHtml(paper.title || "当前论文")}</h3>
        <p>${notes.length} 条笔记。AI 回答和文本选区都可以一键沉淀到这里。</p>
      </article>
      ${notes.length ? notes.map((note) => renderNoteCard(note)).join("") : '<p class="missing-inline">还没有笔记。可以从 AI 回答下方点击“保存为笔记”。</p>'}
    `;
  }

  function renderChallengePanel() {
    if (!challengePanel) return;
    const paper = selectedPaper();
    if (!paper) {
      challengePanel.innerHTML = '<p class="empty-state">请选择论文后开始精读闯关。</p>';
      return;
    }
    if (!state.challenge) {
      challengePanel.innerHTML = `
        <div class="ai-tool-row">
          <span class="ai-tool">练</span>
          <strong>精读闯关</strong>
        </div>
        <article class="challenge-intro">
          <h3>AI 不直接替你读，而是训练你读懂</h3>
          <p>完成 5 个关卡：研究问题、方法流程、图表证据、局限判断、延伸问题。每关先由你回答，再由 AI 纠错评分。</p>
          <button class="challenge-primary" type="button" data-load-challenge>开始闯关</button>
        </article>
      `;
      challengePanel.querySelector("[data-load-challenge]")?.addEventListener("click", loadChallenge);
      return;
    }

    const run = state.challenge;
    const activeStage = run.stages.find((stage) => stage.status !== "passed") || run.stages[run.stages.length - 1];
    challengePanel.innerHTML = `
      <div class="ai-tool-row">
        <span class="ai-tool">练</span>
        <strong>精读闯关</strong>
      </div>
      <section class="challenge-score-card">
        <div>
          <span>完成度</span>
          <strong>${run.completed_count}/${run.total_count}</strong>
        </div>
        <div>
          <span>平均分</span>
          <strong>${run.overall_score || 0}</strong>
        </div>
      </section>
      <div class="challenge-stage-list">
        ${run.stages.map((stage) => renderChallengeStage(stage, activeStage?.id === stage.id)).join("")}
      </div>
      <button class="challenge-primary challenge-report-button" type="button" data-generate-report>生成课堂汇报</button>
      <div id="challengeReportHost">${state.report ? renderChallengeReport(state.report) : ""}</div>
    `;
    challengePanel.querySelectorAll("[data-challenge-form]").forEach((form) => {
      form.addEventListener("submit", submitChallengeAnswer);
    });
    challengePanel.querySelectorAll("[data-retry-challenge]").forEach((button) => {
      button.addEventListener("click", () => {
        state.retryingStageId = button.dataset.retryChallenge || "";
        state.report = null;
        renderChallengePanel();
      });
    });
    challengePanel.querySelector("[data-generate-report]")?.addEventListener("click", loadChallengeReport);
  }

  function renderChallengeStage(stage, isActive) {
    const latest = stage.latest_attempt;
    const isRetrying = state.retryingStageId === stage.id;
    const canAnswer = isRetrying || (!latest && isActive);
    const scoreClass = latest ? scoreTone(latest.score) : "";
    const levelLabel = latest ? challengeLevelLabel(latest.level) : "";
    return `
      <article class="challenge-stage ${stage.status === "passed" ? "is-passed" : ""} ${isActive ? "is-active" : ""}">
        <div class="challenge-stage-head">
          <div>
            <strong>${escapeHtml(stage.title)}</strong>
            <span>${escapeHtml(stage.skill)}</span>
          </div>
          ${latest ? `
            <div class="challenge-score-badge ${scoreClass}">
              <strong>${escapeHtml(latest.score)}</strong>
              <span>分</span>
            </div>
          ` : '<em>未答</em>'}
        </div>
        <p>${escapeHtml(stage.prompt)}</p>
        ${latest ? `
          <div class="challenge-feedback">
            <b>${escapeHtml(levelLabel)}</b>
            <p>${escapeHtml(latest.feedback || "")}</p>
            <p><strong>参考修正：</strong>${escapeHtml(latest.correction || "")}</p>
            <small>${escapeHtml(latest.evidence_hint || "")}</small>
          </div>
          ${!isRetrying ? `
            <button class="challenge-secondary" type="button" data-retry-challenge="${escapeHtml(stage.id)}">重新作答</button>
          ` : ""}
        ` : ""}
        ${!latest && !canAnswer ? `
          <button class="challenge-secondary" type="button" data-retry-challenge="${escapeHtml(stage.id)}">回答本关</button>
        ` : ""}
        ${canAnswer ? `
          <form class="challenge-answer-form" data-challenge-form data-stage-id="${escapeHtml(stage.id)}">
            <textarea rows="4" placeholder="先用自己的话回答，再让 AI 评分纠错。">${latest?.answer ? escapeHtml(latest.answer) : ""}</textarea>
            <button type="submit">提交并评分</button>
          </form>
        ` : ""}
      </article>
    `;
  }

  function renderChallengeReport(report) {
    return `
      <section class="class-report">
        <div class="class-report-cover">
          <p>Class Presentation</p>
          <h2>${escapeHtml(report.paper_title)}</h2>
          <strong>${escapeHtml(report.readiness)} · ${escapeHtml(report.overall_score)} 分</strong>
        </div>
        ${report.sections.map((section) => `
          <article>
            <h3>${escapeHtml(section.title)}</h3>
            <p>${escapeHtml(section.content)}</p>
          </article>
        `).join("")}
        <article>
          <h3>优势</h3>
          <p>${(report.strengths || []).map(escapeHtml).join("、")}</p>
        </article>
        <article>
          <h3>继续改进</h3>
          <p>${(report.improvements || []).map(escapeHtml).join("、")}</p>
        </article>
      </section>
    `;
  }

  function renderNoteCard(note) {
    const kindLabel = { selection: "选区", assistant: "AI", manual: "手写" }[note.kind] || "笔记";
    return `
      <article class="note-source-card">
        <div class="note-source-head">
          <strong>${escapeHtml(note.title || "阅读笔记")}</strong>
          <span>${kindLabel}</span>
        </div>
        ${note.source_text ? `<blockquote>${escapeHtml(note.source_text)}</blockquote>` : ""}
        <p>${escapeHtml(note.content || "")}</p>
        <small>${escapeHtml(note.page_label || note.created_at || "")}</small>
      </article>
    `;
  }

  function selectionLayer() {
    return $("#selectionTextLayer");
  }

  function selectableRootContains(node) {
    const layer = selectionLayer();
    return Boolean(layer && layer.contains(node));
  }

  function selectionToolEnabled() {
    return localStorage.getItem("scholarflow.selectionMode") !== "0";
  }

  function applySelectionMode() {
    const layer = selectionLayer();
    const button = $("#selectionModeButton");
    if (!layer) {
      button?.classList.remove("is-active");
      return;
    }
    if (localStorage.getItem("scholarflow.selectionMode") === null) {
      localStorage.setItem("scholarflow.selectionMode", "0");
    }
    const enabled = selectionToolEnabled();
    layer.hidden = !enabled;
    button?.classList.toggle("is-active", enabled);
    button && (button.textContent = enabled ? "关闭文本层" : "文本层选区");
  }

  function selectedLayerText() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return "";
    if (!selectionToolEnabled()) return "";
    if (!selectableRootContains(selection.anchorNode) || !selectableRootContains(selection.focusNode)) return "";
    return selection.toString().replace(/\s+/g, " ").trim().slice(0, 2000);
  }

  function selectedLayerPageLabel() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return "";
    const anchor = selection.anchorNode?.nodeType === Node.ELEMENT_NODE ? selection.anchorNode : selection.anchorNode?.parentElement;
    return anchor?.closest?.(".selection-page")?.dataset.pageLabel || "";
  }

  function selectedActionText() {
    return selectedLayerText() || (selectionDockText?.value || "").replace(/\s+/g, " ").trim().slice(0, 2000) || clipboardSelectionText;
  }

  async function saveNote(payload) {
    const paper = selectedPaper();
    if (!paper) return setFeedback("请先选择一篇论文。", "error");
    const saved = await fetchJson("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paper_id: paper.id, ...payload }),
    });
    state.dashboard.notes = [saved, ...(state.dashboard.notes || []).filter((note) => note.id !== saved.id)];
    renderAnnotationPanel();
    renderNotesPanel();
    setAiPane("notes");
    setFeedback("已保存到本篇论文的阅读笔记。", "success");
    return saved;
  }

  async function saveSelectionAsNote(text) {
    const paper = selectedPaper();
    if (!paper || !text) return setFeedback("请先选中文字。", "error");
    await saveNote({
      title: "选区摘录",
      kind: "selection",
      source_text: text,
      page_label: selectedLayerPageLabel(),
      anchor_text: text.slice(0, 80),
      content: `待整理摘录：${text}`,
    });
    hideSelectionMenu();
  }

  async function saveAssistantMessageAsNote(messageId) {
    const message = (state.dashboard.assistant_messages || []).find((item) => item.id === messageId);
    if (!message) return setFeedback("没有找到这条 AI 回答。", "error");
    const messages = state.dashboard.assistant_messages || [];
    const messageIndex = messages.findIndex((item) => item.id === messageId);
    const previousUser = [...messages.slice(0, messageIndex)].reverse().find((item) => item.paper_id === message.paper_id && item.role === "user");
    await saveNote({
      title: "AI 回答摘记",
      kind: "assistant",
      assistant_message_id: message.id,
      ai_prompt: previousUser?.content || "",
      source_text: "AI 问答",
      content: message.content,
    });
  }

  function hideSelectionMenu() {
    if (selectionMenu) selectionMenu.hidden = true;
  }

  function showSelectionMenu() {
    const text = selectedLayerText();
    if (!selectionMenu || text.length < 2) return hideSelectionMenu();
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const fallbackRect = $("#readerPanel")?.getBoundingClientRect() || { left: 24, top: 84, right: window.innerWidth - 24 };
    const left = rect.width ? rect.left : fallbackRect.left + 24;
    const top = rect.height ? rect.top : fallbackRect.top + 24;
    selectionMenu.hidden = false;
    selectionMenu.style.left = `${Math.max(8, Math.min(left + window.scrollX, window.innerWidth - selectionMenu.offsetWidth - 12))}px`;
    selectionMenu.style.top = `${Math.max(top + window.scrollY - selectionMenu.offsetHeight - 12, 8)}px`;
  }

  function showSelectionMenuNearElement(element) {
    if (!selectionMenu || !clipboardSelectionText) return;
    const rect = element.getBoundingClientRect();
    selectionMenu.hidden = false;
    selectionMenu.style.left = `${Math.max(8, Math.min(rect.left + window.scrollX, window.innerWidth - selectionMenu.offsetWidth - 12))}px`;
    selectionMenu.style.top = `${Math.min(rect.bottom + window.scrollY + 10, window.innerHeight - selectionMenu.offsetHeight - 12)}px`;
  }

  function scheduleSelectionMenu() {
    window.clearTimeout(selectionMenuTimer);
    selectionMenuTimer = window.setTimeout(showSelectionMenu, 80);
  }

  function highlightSelection() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;
    try {
      const range = selection.getRangeAt(0);
      const mark = document.createElement("mark");
      mark.className = "reader-highlight";
      range.surroundContents(mark);
      selection.removeAllRanges();
      hideSelectionMenu();
      setFeedback("已在文本选择层高亮选中内容。", "success");
    } catch {
      setFeedback("这段选区跨越结构较复杂，建议缩短选区后再高亮。", "error");
    }
  }

  function actOnSelection(action) {
    const text = selectedActionText();
    if (!text) return setFeedback("请先在文本选区层选中文字，或在 PDF 中选中后 Ctrl+C，再点“处理选区”。", "error");
    if (action === "highlight") {
      if (!selectedLayerText()) return setFeedback("原生 PDF 选区无法写回高亮；请点“文本选区”后在文本层高亮。", "error");
      return highlightSelection();
    }
    if (action === "note") {
      return saveSelectionAsNote(text);
    }
    const prompts = {
      explain: `请解释下面这段论文内容，说明它在全文中的作用：\n\n${text}`,
      translate: `请把下面这段论文内容翻译成中文，并保留关键学术术语：\n\n${text}`,
      ask: `请围绕下面这段论文内容回答：它的核心含义、方法细节和可能局限是什么？\n\n${text}`,
    };
    setAiPane("chat");
    assistantInput.value = prompts[action] || prompts.ask;
    assistantInput.focus();
    hideSelectionMenu();
    setFeedback("已把选区放入 AI 问答输入框，可直接发送。", "success");
  }

  function bindSelectionLayer() {
    const layer = selectionLayer();
    if (!layer) return;
    layer.addEventListener("mouseup", scheduleSelectionMenu);
    layer.addEventListener("keyup", scheduleSelectionMenu);
  }

  async function readClipboardSelection(event) {
    if (selectionDock) selectionDock.hidden = false;
    try {
      const text = (await navigator.clipboard.readText()).replace(/\s+/g, " ").trim().slice(0, 2000);
      if (!text) {
        setFeedback("剪贴板里没有文字。请先在 PDF 中选中文字并按 Ctrl+C，或直接粘贴到面板里。", "error");
        return;
      }
      clipboardSelectionText = text;
      if (selectionDockText) selectionDockText.value = text;
      showSelectionMenuNearElement(event.currentTarget);
      setFeedback("已读取复制的选区，可以在面板里选择解释、翻译或向 AI 提问。", "success");
    } catch {
      selectionDockText?.focus();
      setFeedback("浏览器没有允许自动读取剪贴板。请按 Ctrl+V 粘贴到面板文本框。", "error");
    }
  }

  function openSelectionDock() {
    if (!selectionDock) return;
    selectionDock.hidden = false;
    selectionDockText?.focus();
  }

  function actOnDockSelection(action) {
    clipboardSelectionText = (selectionDockText?.value || "").replace(/\s+/g, " ").trim().slice(0, 2000);
    if (!clipboardSelectionText) {
      setFeedback("请先把 PDF 中复制的文字粘贴到选区处理面板。", "error");
      selectionDockText?.focus();
      return;
    }
    actOnSelection(action);
  }

  function renderAll() {
    normalizeSelection();
    renderPaperList();
    renderReader();
    renderTutorialPanel();
    renderAnalysis();
    renderAnnotationPanel();
    renderChallengePanel();
    renderNotesPanel();
    renderMessages();
    applyButtonHelp();
  }

  async function refreshDashboard() {
    state.dashboard = await fetchJson("/api/dashboard");
    normalizeSelection();
  }

  function tutorialModalContent() {
    return `
      <div class="tutorial-route">
        ${tutorialSteps.map((step) => `
          <article>
            <strong>${escapeHtml(step.title)}</strong>
            <p>${escapeHtml(step.body)}</p>
          </article>
        `).join("")}
      </div>
      <div class="tutorial-button-map">
        <h3>按钮怎么用？</h3>
        <p><b>AI 精读</b>：先让系统提炼摘要和追问。</p>
        <p><b>文本层选区</b>：选中论文句子后解释、翻译、提问或加入笔记。</p>
        <p><b>闯关</b>：用 5 个问题检查自己是否真的读懂。</p>
        <p><b>AI 问答</b>：围绕当前论文继续追问细节。</p>
        <p><b>笔记</b>：沉淀选区、AI 回答和你的理解。</p>
      </div>
    `;
  }

  function openTutorialModal() {
    if (!tutorialModal || !tutorialModalBody) return;
    tutorialModalBody.innerHTML = tutorialModalContent();
    tutorialModal.hidden = false;
    state.tutorialOpen = true;
  }

  function closeTutorialModal(remember = false) {
    if (!tutorialModal) return;
    tutorialModal.hidden = true;
    state.tutorialOpen = false;
    if (remember) localStorage.setItem("scholarflow.tutorialSeen", "1");
  }

  async function importSamplePaper() {
    setFeedback("正在导入示例论文...", "busy");
    try {
      const paper = await fetchJson("/api/tutorial/sample-paper", { method: "POST" });
      state.selectedPaperId = paper.id;
      localStorage.setItem("scholarflow.selectedPaperId", paper.id);
      await refreshDashboard();
      state.challenge = null;
      state.report = null;
      state.retryingStageId = "";
      renderAll();
      setAiPane("tutorial");
      closeTutorialModal(true);
      setFeedback("示例论文已导入。建议按教程从 AI 精读开始。", "success");
    } catch (error) {
      setFeedback(error.message, "error");
    }
  }

  async function loadChallenge() {
    const paper = selectedPaper();
    if (!paper) return;
    setFeedback("正在加载精读闯关...", "busy");
    try {
      state.challenge = await fetchJson(`/api/papers/${paper.id}/challenge`);
      state.retryingStageId = "";
      renderChallengePanel();
      setAiPane("challenge");
      setFeedback("精读闯关已准备好。", "success");
    } catch (error) {
      setFeedback(error.message, "error");
    }
  }

  async function submitChallengeAnswer(event) {
    event.preventDefault();
    const paper = selectedPaper();
    const form = event.currentTarget;
    const stageId = form.dataset.stageId;
    const answer = form.querySelector("textarea")?.value.trim();
    if (!paper || !stageId || !answer) return setFeedback("请先填写本关答案。", "error");
    const button = form.querySelector("button");
    button.disabled = true;
    setFeedback("AI 正在纠错评分...", "busy");
    try {
      state.challenge = await fetchJson(`/api/papers/${paper.id}/challenge/${stageId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer }),
      });
      state.report = null;
      state.retryingStageId = "";
      renderChallengePanel();
      setFeedback("本关评分已生成。", "success");
    } catch (error) {
      setFeedback(error.message, "error");
    } finally {
      button.disabled = false;
    }
  }

  async function loadChallengeReport() {
    const paper = selectedPaper();
    if (!paper) return;
    setFeedback("正在生成课堂汇报...", "busy");
    try {
      state.report = await fetchJson(`/api/papers/${paper.id}/challenge-report`);
      renderChallengePanel();
      setFeedback("课堂汇报已生成。", "success");
    } catch (error) {
      setFeedback(error.message, "error");
    }
  }

  async function analyzeSelectedPaper(event) {
    event?.preventDefault();
    event?.stopImmediatePropagation();
    const paper = selectedPaper();
    if (!paper) return setFeedback("请先选择一篇论文。", "error");
    const button = $("#analyzeButton");
    button.disabled = true;
      setFeedback("AI 精读正在分析论文，通常需要十几秒，请稍等...", "busy");
    try {
      const updated = await fetchJson(`/api/papers/${paper.id}/analyze`, { method: "POST" });
      state.dashboard.papers = state.dashboard.papers.map((item) => (item.id === updated.id ? updated : item));
      renderAnalysis();
      setFeedback("AI 精读已完成，可在“当前上下文”查看摘要，也可继续在右侧提问。", "success");
    } catch (error) {
      setFeedback(error.message, "error");
    } finally {
      button.disabled = false;
    }
  }

  async function sendAssistantMessage(event, overrideMessage = "") {
    event?.preventDefault();
    event?.stopImmediatePropagation();
    const paper = selectedPaper();
    const message = (overrideMessage || assistantInput.value || "").trim();
    if (!paper) return setFeedback("请先选择一篇论文。", "error");
    if (!message) return setFeedback("请输入要询问的问题。", "error");
    const sendButton = $("#assistantSendButton");
    sendButton.disabled = true;
    renderMessages([{ role: "user", content: message, paper_id: paper.id }, { role: "assistant", content: "正在阅读论文并组织回答...", paper_id: paper.id }]);
    setFeedback("AI 正在根据当前论文回答...", "busy");
    try {
      const result = await fetchJson(`/api/papers/${paper.id}/assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      state.dashboard.assistant_messages = [...(state.dashboard.assistant_messages || []), ...(result.messages || [])];
      assistantForm.reset();
      renderMessages();
      setFeedback("AI 已回答。", "success");
    } catch (error) {
      renderMessages();
      setFeedback(error.message, "error");
    } finally {
      sendButton.disabled = false;
    }
  }

  async function importPdf(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setFeedback("正在上传并保存 PDF...", "busy");
    try {
      const paper = await fetchJson("/api/papers/import-pdf", { method: "POST", body: formData });
      state.dashboard.papers = [paper, ...(state.dashboard.papers || []).filter((item) => item.id !== paper.id)];
      state.selectedPaperId = paper.id;
      localStorage.setItem("scholarflow.selectedPaperId", paper.id);
      renderAll();
      setFeedback("PDF 已保存，正文已切换为原始 PDF 渲染。", "success");
    } catch (error) {
      setFeedback(error.message, "error");
    } finally {
      event.target.value = "";
    }
  }

  function bindControls() {
    $("#tutorialButton")?.addEventListener("click", () => {
      openTutorialModal();
      setAiPane("tutorial");
    });
    $("#samplePaperButton")?.addEventListener("click", importSamplePaper);
    $("#modalSampleButton")?.addEventListener("click", importSamplePaper);
    $("#closeTutorialButton")?.addEventListener("click", () => closeTutorialModal(false));
    $("#dontShowTutorialButton")?.addEventListener("click", () => closeTutorialModal(true));
    tutorialModal?.addEventListener("click", (event) => {
      if (event.target === tutorialModal) closeTutorialModal(false);
    });
    $("#analyzeButton")?.addEventListener("click", analyzeSelectedPaper, true);
    $("#summaryButton")?.addEventListener("click", (event) => {
      event.preventDefault();
      setAiPane("summary");
      analysisPanel?.scrollTo({ top: 0, behavior: "smooth" });
      setFeedback("已切换到论文摘要。", "success");
    });
    document.querySelectorAll("[data-ai-pane]").forEach((button) => {
      button.addEventListener("click", () => {
        setAiPane(button.dataset.aiPane);
        if (button.dataset.aiPane === "tutorial") renderTutorialPanel();
        if (button.dataset.aiPane === "challenge" && !state.challenge) {
          loadChallenge();
        }
      });
    });
    $("#pdfInput")?.addEventListener("change", importPdf);
    assistantForm?.addEventListener("submit", sendAssistantMessage, true);
    $("#selectionModeButton")?.addEventListener("click", () => {
      const enabled = selectionToolEnabled();
      localStorage.setItem("scholarflow.selectionMode", enabled ? "0" : "1");
      applySelectionMode();
      hideSelectionMenu();
      setFeedback(enabled ? "已恢复 PDF 原貌阅读。原生 PDF 内选中文字不会被网页自动捕捉。" : "已打开文本层选区：在这个文本层中选中文字会自动弹出操作。", "success");
    });
    $("#clipboardSelectionButton")?.addEventListener("click", (event) => {
      openSelectionDock();
      readClipboardSelection(event);
    });
    $("#readClipboardButton")?.addEventListener("click", readClipboardSelection);
    $("#closeSelectionDock")?.addEventListener("click", () => {
      if (selectionDock) selectionDock.hidden = true;
    });
    document.querySelectorAll("[data-dock-action]").forEach((button) => {
      button.addEventListener("click", () => actOnDockSelection(button.dataset.dockAction));
    });
    selectionMenu?.querySelectorAll("[data-selection-action]").forEach((button) => {
      button.addEventListener("click", () => actOnSelection(button.dataset.selectionAction));
    });
    document.addEventListener("selectionchange", () => {
      if (selectionToolEnabled()) scheduleSelectionMenu();
    });
    document.addEventListener("mouseup", scheduleSelectionMenu, true);
    document.addEventListener("keyup", scheduleSelectionMenu, true);
    document.addEventListener("mousedown", (event) => {
      if (!selectionMenu || selectionMenu.hidden || selectionMenu.contains(event.target)) return;
      if (!selectableRootContains(event.target)) hideSelectionMenu();
    });
    $("#attachButton")?.addEventListener("click", () => setFeedback("AI 问答会自动携带当前论文标题、摘要、正文片段和分析记录。", "success"));
    $("#aiModeButton")?.addEventListener("click", () => {
      assistantInput.value = assistantInput.value || "请用三点说明这篇论文的研究问题、方法创新和主要局限。";
      assistantInput.focus();
      setFeedback("AI 精读模式已开启，可以直接发送这个问题。", "success");
    });
  }

  async function boot() {
    bindControls();
    try {
      await refreshDashboard();
      renderAll();
      if (!localStorage.getItem("scholarflow.tutorialSeen")) {
        setAiPane("tutorial");
        openTutorialModal();
      }
    } catch (error) {
      setFeedback(error.message, "error");
    }
  }

  boot();
})();
