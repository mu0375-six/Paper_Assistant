const pageType = document.body.dataset.page;

const statusPanel = document.querySelector("#statusPanel");

const homeRecentPapers = document.querySelector("#homeRecentPapers");
const homeRecentSearches = document.querySelector("#homeRecentSearches");

const searchForm = document.querySelector("#searchForm");
const searchTopicInput = document.querySelector("#searchTopicInput");
const searchSummaryPanel = document.querySelector("#searchSummaryPanel");
const searchResultsPanel = document.querySelector("#searchResultsPanel");
const searchHistoryPanel = document.querySelector("#searchHistoryPanel");

const readerPageIndicator = document.querySelector("#readerPageIndicator");
const readerFeedback = document.querySelector("#readerFeedback");
const zoomOutButton = document.querySelector("#zoomOutButton");
const zoomInButton = document.querySelector("#zoomInButton");
const translationSwitch = document.querySelector("#translationSwitch");
const readerPaperList = document.querySelector("#readerPaperList");
const readerPanel = document.querySelector("#readerPanel");
const analysisPanel = document.querySelector("#analysisPanel");
const analyzeButton = document.querySelector("#analyzeButton");
const translateAbstractButton = document.querySelector("#translateAbstractButton");
const translateContentButton = document.querySelector("#translateContentButton");
const translateAbstractMirror = document.querySelector("#translateAbstractMirror");
const translateContentMirror = document.querySelector("#translateContentMirror");
const sentenceSearchForm = document.querySelector("#sentenceSearchForm");
const sentenceQueryInput = document.querySelector("#sentenceQueryInput");
const sentenceResultsPanel = document.querySelector("#sentenceResultsPanel");
const translationPanel = document.querySelector("#translationPanel");
const assistantMessagesPanel = document.querySelector("#assistantMessagesPanel");
const assistantForm = document.querySelector("#assistantForm");
const assistantInput = document.querySelector("#assistantInput");
const selectionMenu = document.querySelector("#selectionMenu");

const paperForm = document.querySelector("#paperForm");
const pdfInput = document.querySelector("#pdfInput");
const uploadHint = document.querySelector("#uploadHint");
const titleInput = document.querySelector("#titleInput");
const authorsInput = document.querySelector("#authorsInput");
const yearInput = document.querySelector("#yearInput");
const sourceInput = document.querySelector("#sourceInput");
const abstractInput = document.querySelector("#abstractInput");
const contentInput = document.querySelector("#contentInput");
const demoPaperButton = document.querySelector("#demoPaperButton");

const workspaceCurrentPaper = document.querySelector("#workspaceCurrentPaper");
const noteForm = document.querySelector("#noteForm");
const noteTitleInput = document.querySelector("#noteTitleInput");
const noteContentInput = document.querySelector("#noteContentInput");
const notesPanel = document.querySelector("#notesPanel");
const planForm = document.querySelector("#planForm");
const topicInput = document.querySelector("#topicInput");
const planPanel = document.querySelector("#planPanel");
const planHistoryPanel = document.querySelector("#planHistoryPanel");
const writingForm = document.querySelector("#writingForm");
const goalInput = document.querySelector("#goalInput");
const writingPanel = document.querySelector("#writingPanel");
const draftHistoryPanel = document.querySelector("#draftHistoryPanel");

let dashboard = {
  papers: [],
  notes: [],
  search_history: [],
  plans: [],
  writing_drafts: [],
  assistant_messages: [],
};

let selectedPaperId =
  new URLSearchParams(window.location.search).get("paper") ||
  localStorage.getItem("scholarflow.selectedPaperId") ||
  null;
let lastSearch = null;
let readerZoom = Number(localStorage.getItem("scholarflow.readerZoom") || "1");
let translationVisible = true;
let selectedTextForAction = "";
let selectedRangeForAction = null;

function setFeedback(message, type = "") {
  if (!readerFeedback) return;
  readerFeedback.textContent = message;
  readerFeedback.className = `reader-feedback ${type ? `is-${type}` : ""}`;
}

function setButtonBusy(button, busy, label) {
  if (!button) return;
  if (!button.dataset.originalText) {
    button.dataset.originalText = button.textContent.trim();
  }
  button.disabled = busy;
  button.textContent = busy ? label : button.dataset.originalText;
}

function applyReaderZoom() {
  const page = readerPanel?.querySelector(".moonlight-page");
  if (!page) return;
  page.style.transform = `scale(${readerZoom})`;
  page.style.transformOrigin = "top center";
  page.style.marginBottom = `${Math.max(0, (readerZoom - 1) * 650)}px`;
  localStorage.setItem("scholarflow.readerZoom", String(readerZoom));
  setFeedback(`页面缩放：${Math.round(readerZoom * 100)}%`, "success");
}

function toggleTranslationPanel(forceVisible) {
  translationVisible = typeof forceVisible === "boolean" ? forceVisible : !translationVisible;
  const panel = translationPanel?.closest(".assistant-card");
  if (panel) panel.hidden = !translationVisible;
  if (translationSwitch) {
    translationSwitch.textContent = translationVisible ? "ON" : "OFF";
    translationSwitch.classList.toggle("is-on", translationVisible);
  }
  setFeedback(translationVisible ? "翻译结果已显示" : "翻译结果已隐藏", "success");
}

function scrollIntoPanel(selector, message) {
  const target = document.querySelector(selector);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  setFeedback(message, "success");
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function contentToParagraphs(text) {
  return String(text || "")
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitKeywordText(text) {
  return String(text || "")
    .replace(/^keywords?\s*[:：]/i, "")
    .replace(/^关键词\s*[:：]?/i, "")
    .split(/[;；,，、]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 8);
}

function getPaperKeywords(paper) {
  const analysisKeywords = paper.analysis?.keywords || [];
  if (analysisKeywords.length) return analysisKeywords;
  const keywordSource = `${paper.abstract || ""}\n${paper.content || ""}`;
  const match = keywordSource.match(/(?:关键词|关键字|Keywords?)\s*[:：]\s*([^\n。]+)/i);
  return match ? splitKeywordText(match[1]) : [];
}

function getReadableAbstract(paper) {
  const source = `${paper.abstract || ""}\n${paper.content || ""}`;
  const compact = source.replace(/\s+/g, " ").trim();
  const abstractMatch = compact.match(/(?:摘\s*要|摘要|Abstract)\s*[:：]?\s*([\s\S]{30,1200}?)(?:关键词|关键字|Key\s*words?|中图分类号|文献标识码|文章编号)/i);
  if (abstractMatch?.[1]) return abstractMatch[1].trim();

  let abstract = String(paper.abstract || "").trim();
  if (!abstract) return "暂无摘要，请在左侧导入 PDF 或手动补全文献信息。";
  abstract = abstract.replace(/^(摘要|摘\s*要|Abstract)\s*[:：]?\s*/i, "").trim();
  abstract = abstract.replace(/(?:关键词|关键字|Keywords?|Key\s*words?)\s*[:：].*$/is, "").trim();
  return abstract.replace(/\s+/g, " ").trim() || "暂无摘要，请在左侧导入 PDF 或手动补全文献信息。";
}

function inferPaperAuthors(paper) {
  const authors = String(paper.authors || "").trim();
  if (authors && !/^\d{4}(\.\d+)?$/.test(authors)) return authors;
  const compact = String(paper.content || "").replace(/\s+/g, " ");
  const title = String(paper.title || "").replace(/\s+/g, "");
  const titleIndex = title ? compact.replace(/\s+/g, "").indexOf(title) : -1;
  if (titleIndex >= 0) {
    const afterTitle = compact.slice(Math.max(0, compact.indexOf(paper.title) + paper.title.length), compact.indexOf(paper.title) + paper.title.length + 120);
    const match = afterTitle.match(/([\u4e00-\u9fa5]{2,4}[，,\s、]+[\u4e00-\u9fa5]{1,4}[，,\s、]+[\u4e00-\u9fa5]{2,4}(?:[，,\s、]+[\u4e00-\u9fa5]{2,4})?)/);
    if (match) return match[1].replace(/\s+/g, "");
  }
  const authorLine = compact.match(/作者简介[:：][\s\S]{0,120}?([\u4e00-\u9fa5]{2,4})/);
  return authorLine?.[1] || authors || "";
}

function inferPaperOrg(paper) {
  const compact = String(paper.content || "").replace(/\s+/g, " ");
  const match = compact.match(/（([^）]{6,80})）/);
  return match?.[1] || "";
}

function findFigureCaptions(text) {
  const compact = String(text || "").replace(/\s+/g, " ");
  const captions = [];
  const pattern = /(图\s*\d+[^\s。；;，,]{0,4}\s*[^图表]{2,42}|Figure\s*\d+[\s\S]{0,70}?)(?=\s|。|；|;|,|，)/gi;
  let match;
  while ((match = pattern.exec(compact)) && captions.length < 8) {
    const caption = match[0].replace(/\s+/g, " ").trim();
    if (caption.length >= 4 && !captions.includes(caption)) captions.push(caption);
  }
  return captions;
}

function renderMetaValue(value, fallback = "待补充") {
  return escapeHtml(value || fallback);
}

function renderPaperMetaGrid(paper, keywords) {
  const pageCount = paper.pages?.length || paper.page_count || "";
  const authors = inferPaperAuthors(paper);
  const org = inferPaperOrg(paper);
  return `
    <div class="doc-meta-grid">
      <div class="doc-meta-item"><span>作者</span><strong>${renderMetaValue(authors, "作者待补充")}</strong></div>
      <div class="doc-meta-item"><span>来源</span><strong>${renderMetaValue(paper.source, "来源待补充")}</strong></div>
      <div class="doc-meta-item"><span>年份</span><strong>${renderMetaValue(paper.year, "年份待补充")}</strong></div>
      <div class="doc-meta-item"><span>页数</span><strong>${pageCount ? escapeHtml(pageCount) : "待识别"}</strong></div>
    </div>
    ${org ? `<p class="doc-org-line">${escapeHtml(org)}</p>` : ""}
    ${
      keywords.length
        ? `<div class="doc-keyword-row"><span>关键词</span><div>${keywords.map((item) => `<em>${escapeHtml(item)}</em>`).join("")}</div></div>`
        : `<div class="doc-keyword-row"><span>关键词</span><div><em>点击自动高亮后生成</em></div></div>`
    }
  `;
}

function isFigureCaption(text) {
  return /^(图|图表|Fig\.?|Figure|Table|表)\s*[\d一二三四五六七八九十IVXivx.-]*/.test(String(text || "").trim());
}

function renderFigureGallery(paper) {
  const figures = paper.figures || [];
  const captions = findFigureCaptions(paper.content || "");
  if (!figures.length && !captions.length) return "";
  return `
    <section class="doc-figures">
      <h3>图表预览</h3>
      <div class="doc-figure-grid">
        ${
          figures.length
            ? figures.map(
                (figure) => `
              <figure class="doc-figure">
                <img src="${escapeHtml(figure.url)}" alt="${escapeHtml(figure.caption || "Paper figure")}" loading="lazy" />
                <figcaption>${escapeHtml(figure.caption || "Extracted figure")}</figcaption>
              </figure>
            `
              ).join("")
            : captions.map((caption) => `
              <figure class="doc-figure-placeholder">
                <div class="figure-placeholder-box">图表待预览</div>
                <figcaption>${escapeHtml(caption)}</figcaption>
              </figure>
            `).join("")
        }
      </div>
    </section>
  `;
}

function getPaperBodyText(paper) {
  let text = String(paper.content || "");
  text = text.replace(/摘\s*要\s*[:：]?[\s\S]*?(关键词|关键字|Key\s*words?)\s*[:：]?[\s\S]*?(?=\n\s*(中图分类号|文献标识码|文章编号|2026|科学技术创新|1\s*\n|1\.|1\s+))/i, "\n");
  text = text.replace(/基金项目\s*[:：]?[\s\S]*?(?=\n\s*(作者简介|摘\s*要|关键词|1\s*\n|1\.|2026|科学技术创新))/i, "\n");
  text = text.replace(/作者简介\s*[:：]?[\s\S]*?(?=\n\s*(摘\s*要|关键词|1\s*\n|1\.|2026|科学技术创新))/i, "\n");
  const introIndex = text.search(/\n\s*引言\s*\n|^\s*引言\s*\n/m);
  const sectionIndex = text.search(/\n\s*1\s*\n|^\s*1\s*\n|\n\s*1\s+[\u4e00-\u9fa5]/m);
  const startIndex = introIndex >= 0 ? introIndex : sectionIndex;
  if (startIndex > 0) text = text.slice(startIndex);
  const referencesIndex = text.search(/\n\s*参考文献\s*\n/i);
  if (referencesIndex > 0) text = text.slice(0, referencesIndex);
  return text.trim();
}

function renderStructuredBody(text) {
  const lines = String(text || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
  const parts = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const value = paragraph.join("").replace(/\s+/g, " ").trim();
    if (value) parts.push(`<p class="doc-paragraph">${escapeHtml(value)}</p>`);
    paragraph = [];
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const next = lines[index + 1] || "";
    const afterNext = lines[index + 2] || "";

    if (/^(图|表)$/.test(line) && /^\d+/.test(next)) {
      flushParagraph();
      const caption = `${line}${next} ${afterNext}`.trim();
      parts.push(`
        <figure class="doc-figure-placeholder">
          <div class="figure-placeholder-box">图表待预览</div>
          <figcaption>${escapeHtml(caption)}</figcaption>
        </figure>
      `);
      index += afterNext ? 2 : 1;
      continue;
    }

    if (/^(图|表)\s*\d+/.test(line) || /^(Figure|Table)\s+\d+/i.test(line)) {
      flushParagraph();
      parts.push(`
        <figure class="doc-figure-placeholder">
          <div class="figure-placeholder-box">图表待预览</div>
          <figcaption>${escapeHtml(line)}</figcaption>
        </figure>
      `);
      continue;
    }

    if (/^(引言|结论|参考文献)$/.test(line) || /^\d+(\.\d+)?$/.test(line) || /^\d+(\.\d+)*\s*[\u4e00-\u9fa5]/.test(line)) {
      flushParagraph();
      const heading = /^\d+(\.\d+)?$/.test(line) && next ? `${line} ${next}` : line;
      parts.push(`<h3 class="doc-section-title">${escapeHtml(heading)}</h3>`);
      if (/^\d+(\.\d+)?$/.test(line) && next) index += 1;
      continue;
    }

    if (/^(摘\s*要|摘要|关键词|关键字|中图分类号|文献标识码|文章编号|基金项目|作者简介)/.test(line)) {
      flushParagraph();
      continue;
    }

    paragraph.push(line);
    if (/[。！？.!?]$/.test(line) || paragraph.join("").length > 150) flushParagraph();
  }

  flushParagraph();
  return parts.join("");
}

function isSectionHeading(text) {
  const value = String(text || "").trim();
  if (!value || value.length > 34) return false;
  return /^(摘要|关键词|引言|绪论|研究背景|相关工作|方法|实验|结果|讨论|结论|参考文献|附录)$/.test(value)
    || /^\d+(\.\d+)*\s+[\u4e00-\u9fa5A-Za-z]/.test(value)
    || /^[一二三四五六七八九十]+[、.]\s*[\u4e00-\u9fa5A-Za-z]/.test(value);
}

function renderPaperBody(text) {
  const paragraphs = contentToParagraphs(text || "");
  if (!paragraphs.length) return "";

  return paragraphs
    .map((block) => {
      const lines = block
        .split(/\n+/)
        .map((line) => line.trim())
        .filter(Boolean);
      if (!lines.length) return "";

      const firstLine = lines[0].replace(/[:：]\s*$/, "");
      if (isFigureCaption(firstLine)) {
        return `
          <figure class="doc-figure-placeholder">
            <div class="figure-placeholder-box">图表位置</div>
            <figcaption>${escapeHtml(lines.join(" "))}</figcaption>
          </figure>
        `;
      }
      if (isSectionHeading(firstLine)) {
        const body = lines.slice(1).join(" ");
        return `
          <section class="doc-section">
            <h3 class="doc-section-title">${escapeHtml(firstLine)}</h3>
            ${body ? `<p class="doc-paragraph">${escapeHtml(body)}</p>` : ""}
          </section>
        `;
      }

      const normalized = lines.join(" ");
      if (/^\d+(\.\d+)*\s+/.test(normalized) && normalized.length < 120) {
        return `<h4 class="doc-subheading">${escapeHtml(normalized)}</h4>`;
      }
      return `<p class="doc-paragraph">${escapeHtml(normalized)}</p>`;
    })
    .join("");
}

function buildDiscussionParagraphs(paper) {
  const analysis = paper?.analysis || {};
  const summary = splitSentences(analysis.summary || paper?.abstract || "", 6);
  const method = analysis.method ? `具体来说，论文的方法部分强调 ${analysis.method}` : "";
  const findings = (analysis.findings || []).slice(0, 3).join("；");
  const limitations = (analysis.limitations || []).slice(0, 2).join("；");

  return [
    summary.length
      ? `这篇论文的核心可以理解为：${summary[0]}[1]。${summary.slice(1, 3).join("。")}`
      : "点击顶部“自动高亮”后，我会把这篇论文整理成可讨论的精读视角。",
    method ? `${method}[2]。这部分适合重点观察作者如何把研究问题转化为可执行流程。` : "",
    findings ? `从结果和贡献看，值得记录的点包括：${findings}[3]。这些内容可以转写成文献综述里的“已有研究进展”。` : "",
    limitations ? `同时也要留意局限：${limitations}[4]。如果你要继续做研究，这些局限通常就是选题切入口。` : "",
  ].filter(Boolean);
}

function splitSentences(text, limit = 3) {
  return String(text || "")
    .split(/[。！？!?]\s*/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, limit);
}

function formatPaperMeta(paper) {
  return [paper.authors || "作者待补充", paper.year, paper.source].filter(Boolean).join(" · ");
}

function getSelectedPaper() {
  const selected = dashboard.papers.find((item) => item.id === selectedPaperId);
  if (selected) return selected;
  if (dashboard.papers.length) {
    selectedPaperId = dashboard.papers[0].id;
    try {
      localStorage.setItem("scholarflow.selectedPaperId", selectedPaperId);
    } catch (_error) {
      // localStorage can be unavailable in hardened browser modes.
    }
    return dashboard.papers[0];
  }
  return null;
}

function setSelectedPaper(paperId, replaceOnly = true) {
  selectedPaperId = paperId;
  if (!paperId) return;
  localStorage.setItem("scholarflow.selectedPaperId", paperId);
  const url = new URL(window.location.href);
  url.searchParams.set("paper", paperId);
  window.history[replaceOnly ? "replaceState" : "pushState"]({}, "", url.toString());
}

function renderStatus(data) {
  if (!statusPanel) return;
  statusPanel.innerHTML = `
    <article class="status-chip"><strong>${data.paper_count}</strong><span>文献</span></article>
    <article class="status-chip"><strong>${data.analyzed_count}</strong><span>已精读</span></article>
    <article class="status-chip"><strong>${data.search_count || 0}</strong><span>检索</span></article>
    <article class="status-chip"><strong>${(data.note_count || 0) + (data.draft_count || 0)}</strong><span>沉淀</span></article>
  `;
}

function renderHome() {
  if (!homeRecentPapers || !homeRecentSearches) return;
  const latestPapers = (dashboard.papers || []).slice(0, 5);
  const latestSearches = (dashboard.search_history || []).slice(0, 3);

  homeRecentPapers.innerHTML = latestPapers.length
    ? latestPapers
        .map(
          (paper, index) => `
            <a class="library-card home-paper-card ${index === 0 ? "home-paper-card--featured" : ""}" href="/reader?paper=${paper.id}" target="_blank" rel="noreferrer">
              <div>
                <p class="eyebrow">${index === 0 ? "Recommended Next" : `Paper ${index + 1}`}</p>
                <h3>${escapeHtml(paper.title)}</h3>
                <p class="card-meta">${escapeHtml(formatPaperMeta(paper))}</p>
              </div>
              <div class="pill-row">
                <span class="pill">${escapeHtml(paper.source || "未标注来源")}</span>
                <span class="pill ${paper.analysis ? "pill--open" : "pill--meta"}">${paper.analysis ? "已分析" : "待分析"}</span>
              </div>
            </a>
          `
        )
        .join("")
    : `<div class="empty-state">还没有文献。你可以先去研究方向检索页挑选论文，或者在阅读台上传 PDF。</div>`;

  homeRecentSearches.innerHTML = latestSearches.length
    ? latestSearches
        .map(
          (entry) => `
            <a class="history-card home-search-card" href="/discovery">
              <h3>${escapeHtml(entry.query)}</h3>
              <p class="card-meta">${escapeHtml(entry.created_at || "")}</p>
              <p>${entry.results_count || 0} 条候选论文 · 点击继续筛选</p>
            </a>
          `
        )
        .join("")
    : `<div class="empty-state">还没有检索记录。输入研究方向后，这里会自动保存历史。</div>`;
}

function renderSearchSummary() {
  if (!searchSummaryPanel) return;
  if (!lastSearch) {
    searchSummaryPanel.innerHTML = "检索完成后，这里会显示关键词、筛选建议和外部检索入口。";
    return;
  }

  const links = lastSearch.search_links || {};
  searchSummaryPanel.innerHTML = `
    <article class="mini-output">
      <p><strong>研究主题：</strong>${escapeHtml(lastSearch.query)}</p>
      <div class="pill-row">${(lastSearch.keywords || []).map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</div>
      <p><strong>聚焦建议：</strong>${escapeHtml(lastSearch.focus || "")}</p>
      <ul>${(lastSearch.screening_tips || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      <div class="button-row">
        <a class="button button--ghost" href="${links.cnki}" target="_blank" rel="noreferrer">知网检索</a>
        <a class="button button--ghost" href="${links.arxiv}" target="_blank" rel="noreferrer">arXiv</a>
        <a class="button button--ghost" href="${links.semantic_scholar}" target="_blank" rel="noreferrer">Semantic Scholar</a>
      </div>
    </article>
  `;
}

async function translateCandidate(index, targetLanguage) {
  const result = lastSearch.results[index];
  const data = await fetchJson("/api/discovery/translate-result", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...result, target_language: targetLanguage }),
  });
  result.translation = data;
  renderSearchResults();
}

async function downloadAndOpenPdf(result) {
  if (!result?.pdf_url) return;
  const data = await fetchJson("/api/discovery/download-pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pdf_url: result.pdf_url, title: result.title }),
  });
  const link = document.createElement("a");
  link.href = data.local_url;
  link.download = data.filename || `${result.title || "paper"}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.open(data.local_url, "_blank");
}

function renderSearchResults() {
  if (!searchResultsPanel) return;
  if (!lastSearch?.results?.length) {
    searchResultsPanel.innerHTML = `<div class="empty-state">输入研究方向后，这里会显示候选论文。卡片底部会出现“下载并打开 PDF”“加入文献库”“查看文本”等入口。</div>`;
    return;
  }

  searchResultsPanel.innerHTML = lastSearch.results
    .map(
      (paper, index) => `
        <article class="search-card ${paper.pdf_url ? "has-pdf" : ""}">
          <div class="candidate-rank">候选 ${index + 1}</div>
          <h3>${index + 1}. ${escapeHtml(paper.title)}</h3>
          <p class="card-meta">${escapeHtml(paper.authors || "作者待补充")} ${paper.year ? `· ${escapeHtml(paper.year)}` : ""}</p>
          <div class="pill-row">
            <span class="pill">${escapeHtml(paper.source || "未标注来源")}</span>
            <span class="pill ${paper.source_type === "open-access" ? "pill--open" : "pill--meta"}">${paper.source_type === "open-access" ? "开放获取" : "需外部访问"}</span>
          </div>
          <p>${escapeHtml(paper.abstract || paper.excerpt || "暂无摘要")}</p>
          ${
            paper.translation
              ? `<article class="mini-output"><p>${escapeHtml(paper.translation.translated_text)}</p></article>`
              : ""
          }
          <div class="button-row">
            <button class="button button--primary" type="button" data-save-result="${index}">加入文献库</button>
            <button class="button button--ghost" type="button" data-translate-result="${index}">${paper.translation ? "切换译文" : "中英互译"}</button>
            ${paper.pdf_url ? `<button class="button button--pdf" type="button" data-open-pdf="${index}">下载并打开 PDF</button>` : `<span class="pdf-missing-label">暂无直接 PDF</span>`}
            ${paper.text_url ? `<a class="button button--ghost" href="${paper.text_url}" target="_blank" rel="noreferrer">查看文本</a>` : ""}
          </div>
        </article>
      `
    )
    .join("");

  searchResultsPanel.querySelectorAll("[data-save-result]").forEach((button) => {
    button.addEventListener("click", async () => {
      const result = lastSearch.results[Number(button.dataset.saveResult)];
      const saved = await fetchJson("/api/discovery/save-result", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      window.open(`/reader?paper=${saved.id}`, "_blank");
    });
  });

  searchResultsPanel.querySelectorAll("[data-translate-result]").forEach((button) => {
    button.addEventListener("click", async () => {
      const index = Number(button.dataset.translateResult);
      const current = lastSearch.results[index].translation?.target_language || "zh";
      const target = current === "zh" ? "en" : "zh";
      await translateCandidate(index, target);
    });
  });

  searchResultsPanel.querySelectorAll("[data-open-pdf]").forEach((button) => {
    button.addEventListener("click", async () => {
      const result = lastSearch.results[Number(button.dataset.openPdf)];
      await downloadAndOpenPdf(result);
    });
  });
}

function renderSearchHistory() {
  if (!searchHistoryPanel) return;
  const history = dashboard.search_history || [];
  searchHistoryPanel.innerHTML = history.length
    ? history
        .map(
          (entry) => `
            <article class="history-card history-card--clickable" data-history-id="${escapeHtml(entry.id || "")}">
              <h3>${escapeHtml(entry.query)}</h3>
              <p class="card-meta">${escapeHtml(entry.created_at || "")}</p>
              <div class="pill-row">${(entry.keywords || []).slice(0, 4).map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</div>
              <p>共返回 ${entry.results_count || 0} 条候选论文 · 点击恢复候选结果</p>
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">还没有检索历史。</div>`;

  searchHistoryPanel.querySelectorAll("[data-history-id]").forEach((card) => {
    card.addEventListener("click", async () => {
      const historyId = card.dataset.historyId;
      if (!historyId) return;
      searchSummaryPanel.innerHTML = "正在恢复这次检索的候选论文...";
      if (searchResultsPanel) searchResultsPanel.innerHTML = "";
      try {
        lastSearch = await fetchJson(`/api/discovery/history/${historyId}`);
        if (searchTopicInput) searchTopicInput.value = lastSearch.query || "";
        renderSearchSummary();
        renderSearchResults();
        document.querySelector("#candidateSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (error) {
        searchSummaryPanel.innerHTML = `<div class="empty-state">${escapeHtml(error.message || "恢复历史失败。")}</div>`;
      }
    });
  });
}

function updateReaderPageIndicator(paper) {
  if (!readerPageIndicator) return;
  const pageCount =
    paper?.pages?.length ||
    Math.max(1, Math.ceil((paper?.content || "").length / 2200));
  readerPageIndicator.textContent = `1 / ${pageCount}`;
}

function renderReaderPaperList() {
  if (!readerPaperList) return;
  const papers = dashboard.papers || [];
  readerPaperList.innerHTML = papers.length
    ? papers
        .map(
          (paper) => `
            <article class="paper-entry ${paper.id === selectedPaperId ? "paper-entry--selected" : ""}" data-paper-id="${paper.id}">
              <h3>${escapeHtml(paper.title)}</h3>
              <p class="card-meta">${escapeHtml(formatPaperMeta(paper))}</p>
              <div class="pill-row">
                <span class="pill">${escapeHtml(paper.source || "未标注来源")}</span>
                <span class="pill ${paper.analysis ? "pill--open" : "pill--meta"}">${paper.analysis ? "已分析" : "待分析"}</span>
              </div>
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">还没有文献。你可以上传 PDF，或在研究方向检索页把候选论文加入文献库。</div>`;

  readerPaperList.querySelectorAll("[data-paper-id]").forEach((element) => {
    element.addEventListener("click", () => {
      setSelectedPaper(element.dataset.paperId);
      renderReaderPaperList();
      renderReaderPanel();
      renderAnalysisPanel();
      renderWorkspaceCurrentPaper();
      renderNotes();
      renderAssistantMessages();
    });
  });
}

function renderReaderPanel() {
  if (!readerPanel) return;
  const paper = getSelectedPaper();
  if (!paper) {
    readerPanel.innerHTML = "从左侧文献库选择一篇论文后，这里会展示完整阅读视图。";
    return;
  }

  updateReaderPageIndicator(paper);

  if (titleInput) titleInput.value = paper.title || "";
  if (authorsInput) authorsInput.value = paper.authors || "";
  if (yearInput) yearInput.value = paper.year || "";
  if (sourceInput) sourceInput.value = paper.source || "";
  if (abstractInput) abstractInput.value = paper.abstract || "";
  if (contentInput) contentInput.value = paper.content || "";

  const bodyHtml = renderStructuredBody(getPaperBodyText(paper));
  const keywords = getPaperKeywords(paper);
  const abstractText = getReadableAbstract(paper);
  const figuresHtml = renderFigureGallery(paper);
  const pdfPreviewUrl = paper.downloaded_pdf_url || paper.pdf_url || "";

  readerPanel.innerHTML = `
    <div class="moonlight-page">
      <p class="doc-topline">- 1 - ${escapeHtml(paper.source || "ScholarFlow Imported Paper")} ${paper.year ? escapeHtml(paper.year) : ""}</p>
      <h2 class="moonlight-title">${escapeHtml(paper.title)}</h2>
      <p class="moonlight-authors">${escapeHtml(paper.authors || "作者待补充")}</p>
      <p class="moonlight-org">${escapeHtml(paper.source || "来源待补充")}</p>
      <h3 class="doc-abstract-title">摘要</h3>
      <div class="doc-abstract">${escapeHtml(paper.abstract || "暂无摘要，请在左侧导入 PDF 或手动补全文献信息。")}</div>
      ${
        keywords.length
          ? `<p class="doc-keywords"><strong>关键词：</strong>${keywords.map((item) => escapeHtml(item)).join("；")}</p>`
          : ""
      }
      <h3 class="doc-body-title">引言与正文</h3>
      <div class="doc-body-columns">
        ${
          bodyHtml
            ? bodyHtml
            : `<p class="doc-paragraph">当前还没有完整正文。你可以上传 PDF，系统会自动抽取全文；也可以在左侧手动粘贴正文片段。</p>`
        }
      </div>
      ${
        paper.downloaded_pdf_url
          ? `<div class="doc-actions"><a class="button button--ghost" href="${paper.downloaded_pdf_url}" target="_blank" rel="noreferrer">打开已下载 PDF</a></div>`
          : ""
      }
    </div>
  `;
  applyReaderZoom();
}

function renderAnalysisPanel() {
  if (!analysisPanel) return;
  const paper = getSelectedPaper();
  if (!paper) {
    analysisPanel.innerHTML = `<article class="assistant-card empty-state">点击“自动高亮”后，这里会出现关键词、三行摘要和精读问题。</article>`;
    return;
  }

  if (!paper.analysis) {
    analysisPanel.innerHTML = `
      <article class="assistant-card">
        <div class="assistant-card-head">
          <h3>阅读辅助</h3>
        </div>
        <p class="helper-text">这篇论文还没有生成阅读分析。点击顶部“自动高亮”后，右侧会出现关键词词典、三行摘要和精读问题。</p>
      </article>
    `;
    return;
  }

  const analysis = paper.analysis;
  const conciseSummary = splitSentences(analysis.summary || "", 3);
  const quickQuestions = (analysis.reading_questions || []).slice(0, 6);

  analysisPanel.innerHTML = `
    <article class="assistant-card">
      <div class="assistant-card-head">
        <h3>关键词词典</h3>
      </div>
      <div class="keyword-cloud">
        ${(analysis.keywords || []).map((item) => `<span class="keyword-chip">${escapeHtml(item)}</span>`).join("") || `<span class="helper-text">暂无关键词</span>`}
      </div>
    </article>

    <article class="assistant-card">
      <div class="assistant-card-head">
        <h3>三行摘要</h3>
      </div>
      <div class="summary-lines">
        ${
          conciseSummary.length
            ? conciseSummary
                .map(
                  (item, index) => `
                    <div class="summary-line">
                      <span class="summary-index">${index + 1}</span>
                      <div>${escapeHtml(item)}</div>
                    </div>
                  `
                )
                .join("")
            : `<div class="helper-text">暂无摘要分析。</div>`
        }
      </div>
    </article>

    <article class="assistant-card">
      <div class="assistant-card-head">
        <h3>精读问题</h3>
      </div>
      <div class="question-pills">
        ${
          quickQuestions.length
            ? quickQuestions.map((item) => `<button class="question-pill" type="button" data-quick-question="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join("")
            : `<span class="helper-text">暂无推荐问题。</span>`
        }
      </div>
    </article>

    <details class="assistant-card analysis-details">
      <summary>摘要</summary>
      <div class="analysis-meta">
        <div class="analysis-meta-item"><strong>研究问题</strong><span>${escapeHtml(analysis.research_problem || "暂无")}</span></div>
        <div class="analysis-meta-item"><strong>方法概述</strong><span>${escapeHtml(analysis.method || "暂无")}</span></div>
        <div class="analysis-meta-item"><strong>主要发现</strong><span>${escapeHtml((analysis.findings || []).join("；") || "暂无")}</span></div>
        <div class="analysis-meta-item"><strong>局限性</strong><span>${escapeHtml((analysis.limitations || []).join("；") || "暂无")}</span></div>
      </div>
    </details>
  `;

  analysisPanel.querySelectorAll("[data-quick-question]").forEach((button) => {
    button.addEventListener("click", () => {
      if (assistantInput) {
        assistantInput.value = button.dataset.quickQuestion;
        assistantInput.focus();
      }
    });
  });
}

function renderWorkspaceCurrentPaper() {
  if (!workspaceCurrentPaper) return;
  const paper = getSelectedPaper();
  if (!paper) {
    workspaceCurrentPaper.innerHTML = "先去阅读台选择一篇论文，这里才会展开对应的笔记和写作任务。";
    return;
  }

  workspaceCurrentPaper.innerHTML = `
    <article class="current-paper-card">
      <h3>${escapeHtml(paper.title)}</h3>
      <p class="card-meta">${escapeHtml(formatPaperMeta(paper))}</p>
      <div class="pill-row">
        <span class="pill">${escapeHtml(paper.source || "未标注来源")}</span>
        <span class="pill ${paper.analysis ? "pill--open" : "pill--meta"}">${paper.analysis ? "已分析" : "待分析"}</span>
      </div>
      <p>${escapeHtml((paper.abstract || "").slice(0, 220) || "暂无摘要。")}</p>
      <div class="button-row">
        <a class="button button--ghost" href="/reader?paper=${paper.id}" target="_blank" rel="noreferrer">回到阅读台</a>
      </div>
    </article>
  `;
}

function renderNotes() {
  if (!notesPanel) return;
  const paper = getSelectedPaper();
  if (!paper) {
    notesPanel.innerHTML = `<div class="empty-state">先选择一篇论文，然后这里会显示与这篇论文关联的阅读笔记。</div>`;
    return;
  }

  const notes = (dashboard.notes || []).filter((item) => item.paper_id === paper.id).slice().reverse();
  notesPanel.innerHTML = notes.length
    ? notes
        .map(
          (note) => `
            <article class="note-card">
              <h3>${escapeHtml(note.title)}</h3>
              <p>${escapeHtml(note.content)}</p>
              <p class="card-meta">${escapeHtml(note.updated_at || "")}</p>
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">这篇论文还没有笔记。</div>`;
}

function renderPlanHistory() {
  if (!planHistoryPanel) return;
  const items = dashboard.plans || [];
  planHistoryPanel.innerHTML = items.length
    ? items
        .slice(0, 4)
        .map(
          (item) => `
            <article class="history-card">
              <h3>${escapeHtml(item.topic)}</h3>
              <p class="card-meta">${escapeHtml(item.created_at || "")}</p>
              <p>${escapeHtml((item.result?.topic_summary || "").slice(0, 160))}</p>
            </article>
          `
        )
        .join("")
    : "";
}

function renderDraftHistory() {
  if (!draftHistoryPanel) return;
  const items = dashboard.writing_drafts || [];
  draftHistoryPanel.innerHTML = items.length
    ? items
        .slice(0, 4)
        .map(
          (item) => `
            <article class="history-card">
              <h3>${escapeHtml(item.goal || item.topic)}</h3>
              <p class="card-meta">${escapeHtml(item.created_at || "")}</p>
              <p>${escapeHtml((item.result?.abstract_draft || "").slice(0, 160))}</p>
            </article>
          `
        )
        .join("")
    : "";
}

function renderAssistantMessages() {
  if (!assistantMessagesPanel) return;
  const paper = getSelectedPaper();
  if (!paper) {
    assistantMessagesPanel.innerHTML = "先选择一篇论文，然后就可以继续追问方法、贡献、局限或实验细节。";
    assistantMessagesPanel.classList.add("empty-state");
    return;
  }

  const messages = (dashboard.assistant_messages || []).filter((item) => item.paper_id === paper.id).slice(-8);
  assistantMessagesPanel.classList.remove("empty-state");
  assistantMessagesPanel.innerHTML = messages.length
    ? messages
        .map(
          (item) => `
            <article class="assistant-message assistant-message--${item.role}">
              <h3>${item.role === "assistant" ? "AI 助手" : "你"}</h3>
              <p>${escapeHtml(item.content)}</p>
              ${
                item.followups?.length
                  ? `<div class="pill-row">${item.followups.map((q) => `<span class="pill pill--meta">${escapeHtml(q)}</span>`).join("")}</div>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">还没有对话记录。你可以从右侧直接开始问问题。</div>`;
}

async function refreshStatus() {
  const status = await fetchJson("/api/status");
  renderStatus(status);
}

async function refreshDashboard() {
  dashboard = await fetchJson("/api/dashboard");
  if (selectedPaperId && !dashboard.papers.find((item) => item.id === selectedPaperId)) {
    selectedPaperId = null;
  }
  if (!selectedPaperId && dashboard.papers.length) {
    setSelectedPaper(dashboard.papers[0].id);
  }

  renderHome();
  renderSearchHistory();
  renderReaderPaperList();
  renderReaderPanel();
  renderAnalysisPanel();
  renderWorkspaceCurrentPaper();
  renderNotes();
  renderPlanHistory();
  renderDraftHistory();
  renderAssistantMessages();
}

async function analyzeSelectedPaper() {
  const paper = getSelectedPaper();
  if (!paper) {
    setFeedback("请先从左侧选择一篇论文。", "error");
    return;
  }
  try {
    setButtonBusy(analyzeButton, true, "分析中...");
    setFeedback("正在生成关键词、三行摘要和精读问题...", "busy");
    await fetchJson(`/api/papers/${paper.id}/analyze`, { method: "POST" });
    await refreshDashboard();
    analysisPanel?.classList.add("is-highlighted");
    setFeedback("阅读分析已更新。", "success");
  } catch (error) {
    setFeedback(error.message || "阅读分析失败。", "error");
  } finally {
    setButtonBusy(analyzeButton, false);
  }
}

async function translateSelectedPaper(scope, targetLanguage = "zh") {
  const paper = getSelectedPaper();
  if (!paper || !translationPanel) {
    setFeedback("请先从左侧选择一篇论文。", "error");
    return;
  }
  const button = scope === "abstract" ? translateAbstractButton : translateContentButton;
  try {
    setButtonBusy(button, true, "翻译中...");
    setFeedback(`正在翻译${scope === "abstract" ? "摘要" : "正文"}...`, "busy");
    toggleTranslationPanel(true);
    translationPanel.innerHTML = "正在生成翻译...";
    const data = await fetchJson(`/api/papers/${paper.id}/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, target_language: targetLanguage }),
    });

    translationPanel.innerHTML = `
      <article class="mini-output">
        <h3>${scope === "abstract" ? "摘要翻译" : "正文翻译"}</h3>
        <p>${escapeHtml(data.translated_text)}</p>
      </article>
    `;
    setFeedback("翻译结果已更新。", "success");
  } catch (error) {
    translationPanel.innerHTML = `<div class="empty-state">${escapeHtml(error.message || "翻译失败。")}</div>`;
    setFeedback(error.message || "翻译失败。", "error");
  } finally {
    setButtonBusy(button, false);
  }
}

async function searchSentences(event) {
  event.preventDefault();
  const paper = getSelectedPaper();
  const query = sentenceQueryInput?.value.trim();
  if (!paper || !query || !sentenceResultsPanel) {
    setFeedback("请选择论文并输入检索词。", "error");
    return;
  }
  const submitButton = sentenceSearchForm?.querySelector("button");
  try {
    setButtonBusy(submitButton, true, "检索中...");
    setFeedback("正在检索正文句子...", "busy");
    sentenceResultsPanel.innerHTML = "正在检索...";
    const data = await fetchJson(`/api/papers/${paper.id}/sentence-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    sentenceResultsPanel.innerHTML = data.matches.length
      ? data.matches
          .map(
            (item) => `
              <article class="sentence-card">
                <h3>命中句 ${item.index}</h3>
                <p>${escapeHtml(item.sentence)}</p>
              </article>
            `
          )
          .join("")
      : `<div class="empty-state">没有找到匹配语句，请换一个术语或更短的关键词。</div>`;
    setFeedback(data.matches.length ? `找到 ${data.matches.length} 条匹配句。` : "没有找到匹配句。", data.matches.length ? "success" : "");
  } catch (error) {
    sentenceResultsPanel.innerHTML = `<div class="empty-state">${escapeHtml(error.message || "检索失败。")}</div>`;
    setFeedback(error.message || "检索失败。", "error");
  } finally {
    setButtonBusy(submitButton, false);
  }
}

async function sendAssistantMessage(event) {
  event.preventDefault();
  const paper = getSelectedPaper();
  const message = assistantInput?.value.trim();
  if (!paper || !message) {
    setFeedback("请选择论文并输入问题。", "error");
    return;
  }
  const submitButton = assistantForm?.querySelector('button[type="submit"]');
  try {
    setButtonBusy(submitButton, true, "思考中...");
    setFeedback("AI 助手正在阅读上下文并回答...", "busy");
    await fetchJson(`/api/papers/${paper.id}/assistant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    assistantForm.reset();
    await refreshDashboard();
    setFeedback("AI 助手已回复。", "success");
  } catch (error) {
    setFeedback(error.message || "AI 助手回复失败。", "error");
  } finally {
    setButtonBusy(submitButton, false);
  }
}

async function handleSearchSubmit(event) {
  event.preventDefault();
  const topic = searchTopicInput?.value.trim();
  if (!topic) {
    searchSummaryPanel.innerHTML = `<div class="empty-state">请先输入研究方向。</div>`;
    return;
  }
  searchSummaryPanel.innerHTML = "正在检索研究方向...";
  if (searchResultsPanel) searchResultsPanel.innerHTML = "";
  lastSearch = await fetchJson("/api/discovery/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  if (topicInput) topicInput.value = topic;
  renderSearchSummary();
  renderSearchResults();
  document.querySelector("#candidateSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
  await refreshStatus();
  await refreshDashboard();
}

async function handlePdfImport(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (uploadHint) uploadHint.textContent = `正在导入 ${file.name} ...`;
  const formData = new FormData();
  formData.append("file", file);

  try {
    const data = await fetchJson("/api/papers/import-pdf", { method: "POST", body: formData });
    setSelectedPaper(data.id);
    if (titleInput) titleInput.value = data.title || "";
    if (authorsInput) authorsInput.value = data.authors || "";
    if (yearInput) yearInput.value = data.year || "";
    if (sourceInput) sourceInput.value = data.source || "";
    if (abstractInput) abstractInput.value = data.abstract || "";
    if (contentInput) contentInput.value = data.content || "";
    if (uploadHint) {
      uploadHint.textContent = `已提取并保存 ${data.import_meta.filename}，共 ${data.import_meta.page_count} 页。`;
    }
    await refreshStatus();
    await refreshDashboard();
  } catch (error) {
    if (uploadHint) uploadHint.textContent = error.message;
  }
}

async function handlePaperSave(event) {
  event.preventDefault();
  const payload = {
    id: selectedPaperId || "",
    title: titleInput?.value.trim(),
    authors: authorsInput?.value.trim(),
    year: yearInput?.value.trim(),
    source: sourceInput?.value.trim(),
    abstract: abstractInput?.value.trim(),
    content: contentInput?.value.trim(),
  };

  if (!payload.title) {
    if (uploadHint) uploadHint.textContent = "请先填写论文标题。";
    return;
  }

  const saved = await fetchJson("/api/papers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setSelectedPaper(saved.id);
  if (uploadHint) uploadHint.textContent = "文献信息已保存。";
  await refreshStatus();
  await refreshDashboard();
}

async function handleNoteSave(event) {
  event.preventDefault();
  const paper = getSelectedPaper();
  if (!paper) return;
  await fetchJson("/api/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paper_id: paper.id,
      title: noteTitleInput?.value.trim(),
      content: noteContentInput?.value.trim(),
    }),
  });
  noteForm.reset();
  await refreshStatus();
  await refreshDashboard();
}

async function handlePlanGenerate(event) {
  event.preventDefault();
  const topic = topicInput?.value.trim();
  if (!topic || !planPanel) return;
  planPanel.innerHTML = "正在生成研究计划...";
  const paperIds = (dashboard.papers || []).map((item) => item.id);
  const data = await fetchJson("/api/research-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, paper_ids: paperIds }),
  });

  planPanel.innerHTML = `
    <article class="mini-output">
      <h3>主题概述</h3>
      <p>${escapeHtml(data.topic_summary || "")}</p>
      <h3>阅读路线</h3>
      <ul>${(data.reading_route || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      <h3>产出建议</h3>
      <ul>${(data.output_targets || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </article>
  `;
  await refreshStatus();
  await refreshDashboard();
}

async function handleWritingGenerate(event) {
  event.preventDefault();
  const topic = topicInput?.value.trim();
  const goal = goalInput?.value.trim();
  if (!topic || !writingPanel) return;
  writingPanel.innerHTML = "正在生成写作草稿...";
  const paperIds = (dashboard.papers || []).map((item) => item.id);
  const data = await fetchJson("/api/writing-pack", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, goal, paper_ids: paperIds }),
  });

  writingPanel.innerHTML = `
    <article class="mini-output">
      <h3>提纲</h3>
      <ul>${(data.outline || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      <h3>摘要草稿</h3>
      <p>${escapeHtml(data.abstract_draft || "")}</p>
      <h3>Related Work 草稿</h3>
      <p>${escapeHtml(data.related_work_draft || "")}</p>
    </article>
  `;
  await refreshStatus();
  await refreshDashboard();
}

function fillDemoPaper() {
  if (titleInput) titleInput.value = "Large Language Models for Academic Search and Review";
  if (authorsInput) authorsInput.value = "A. Researcher; B. Student";
  if (yearInput) yearInput.value = "2025";
  if (sourceInput) sourceInput.value = "arXiv";
  if (abstractInput) {
    abstractInput.value =
      "This paper studies how large language models can assist academic search, literature review, and early-stage research planning. It compares retrieval support, summarization quality, and writing assistance across several workflows.";
  }
  if (contentInput) {
    contentInput.value =
      "Introduction: Academic work often begins with broad search and rapid filtering. The paper argues that LLMs are useful when they help researchers compare papers, identify research gaps, and scaffold outlines.\n\nMethod: The authors evaluate a mixed workflow combining search, structured reading notes, and iterative writing.\n\nFindings: LLM support improves early synthesis speed but still requires human validation for factual accuracy and citation control.";
  }
  if (uploadHint) uploadHint.textContent = "已填入一篇演示论文，你可以直接保存后查看阅读台效果。";
}

function renderAnalysisPanel() {
  if (!analysisPanel) return;
  const paper = getSelectedPaper();
  if (!paper) {
    analysisPanel.innerHTML = `<article class="assistant-card empty-state">点击“自动高亮”后，这里会出现讨论摘要、关键词和精读问题。</article>`;
    return;
  }

  if (!paper.analysis) {
    analysisPanel.innerHTML = `
      <article class="assistant-card discussion-card">
        <div class="assistant-card-head">
          <h3>讨论</h3>
          <span class="mini-kicker">Waiting</span>
        </div>
        <p>这篇论文还没有生成 AI 阅读分析。点击顶部“自动高亮”，右侧会像精读助手一样给出讨论摘要、关键词和可追问问题。</p>
      </article>
    `;
    return;
  }

  const analysis = paper.analysis;
  const discussion = buildDiscussionParagraphs(paper);
  const quickQuestions = (analysis.reading_questions || []).slice(0, 4);

  analysisPanel.innerHTML = `
    <article class="assistant-card discussion-card">
      <div class="assistant-card-head">
        <h3>讨论</h3>
        <button class="assistant-collapse" type="button" title="这部分是 AI 根据论文内容生成的讨论摘要">⌄</button>
      </div>
      <div class="discussion-body">
        ${discussion.map((item) => `<p>${escapeHtml(item).replace(/\[(\d+)\]/g, '<sup>[$1]</sup>')}</p>`).join("")}
      </div>
    </article>

    <article class="assistant-card keyword-panel">
      <div class="assistant-card-head">
        <h3>关键词词典</h3>
      </div>
      <div class="keyword-cloud">
        ${(analysis.keywords || []).map((item) => `<span class="keyword-chip">${escapeHtml(item)}</span>`).join("") || `<span class="helper-text">暂无关键词</span>`}
      </div>
    </article>

    <article class="assistant-card question-panel">
      <div class="assistant-card-head">
        <h3>推荐追问</h3>
      </div>
      <div class="question-pills">
        ${
          quickQuestions.length
            ? quickQuestions.map((item) => `<button class="question-pill" type="button" data-quick-question="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join("")
            : `<button class="question-pill" type="button" data-quick-question="这篇论文的核心贡献是什么？">这篇论文的核心是什么？</button>
               <button class="question-pill" type="button" data-quick-question="这篇论文与已有研究有什么不同？">与已有研究有什么不同？</button>
               <button class="question-pill" type="button" data-quick-question="这篇论文有什么局限性？">有什么局限性？</button>`
        }
      </div>
    </article>
  `;

  analysisPanel.querySelectorAll("[data-quick-question]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!assistantInput) return;
      assistantInput.value = button.dataset.quickQuestion;
      assistantInput.focus();
      scrollIntoPanel(".assistant-card--chat", "已把推荐问题填入 AI 提问框。");
    });
  });
}

async function submitAssistantPrompt(message, clearForm = true) {
  const paper = getSelectedPaper();
  if (!paper || !message) {
    setFeedback("请先选择论文并输入问题。", "error");
    return;
  }

  const submitButton = assistantForm?.querySelector('button[type="submit"]');
  try {
    setButtonBusy(submitButton, true, "思考中...");
    setFeedback("AI 助手正在阅读上下文并回答...", "busy");
    await fetchJson(`/api/papers/${paper.id}/assistant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (clearForm) assistantForm?.reset();
    await refreshDashboard();
    scrollIntoPanel(".assistant-card--chat", "AI 助手已回复。");
  } catch (error) {
    setFeedback(error.message || "AI 助手回复失败。", "error");
  } finally {
    setButtonBusy(submitButton, false);
  }
}

async function sendAssistantMessage(event) {
  event.preventDefault();
  await submitAssistantPrompt(assistantInput?.value.trim(), true);
}

async function translateSelectedPaper(scope) {
  const paper = getSelectedPaper();
  if (!paper) {
    setFeedback("请先从左侧选择一篇论文。", "error");
    return;
  }

  const button = scope === "abstract" ? translateAbstractButton : translateContentButton;
  const target = scope === "abstract" ? "摘要" : "正文的核心段落";
  const prompt = `请把当前论文的${target}翻译成中文，并保留学术术语。如果原文已经是中文，请改为提炼成更容易理解的中文解释。`;
  try {
    setButtonBusy(button, true, "发送中...");
    await submitAssistantPrompt(prompt, false);
  } finally {
    setButtonBusy(button, false);
  }
}

function hideSelectionMenu() {
  if (!selectionMenu) return;
  selectionMenu.hidden = true;
}

function showSelectionMenuFromRange(range) {
  if (!selectionMenu || !range) return;
  const rect = range.getBoundingClientRect();
  if (!rect.width && !rect.height) return;
  selectionMenu.hidden = false;
  selectionMenu.style.left = `${Math.min(window.innerWidth - 360, Math.max(16, rect.left + rect.width / 2 - 170))}px`;
  selectionMenu.style.top = `${Math.max(76, rect.top - 52)}px`;
}

function updateSelectionMenu() {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || !readerPanel) {
    hideSelectionMenu();
    return;
  }
  const range = selection.getRangeAt(0);
  if (!readerPanel.contains(range.commonAncestorContainer)) {
    hideSelectionMenu();
    return;
  }
  selectedTextForAction = selection.toString().trim().slice(0, 1600);
  selectedRangeForAction = range.cloneRange();
  if (!selectedTextForAction) {
    hideSelectionMenu();
    return;
  }
  showSelectionMenuFromRange(range);
}

function restoreSelectionRange() {
  if (!selectedRangeForAction) return;
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(selectedRangeForAction);
}

async function handleSelectionAction(action) {
  const text = selectedTextForAction;
  if (!text) return;

  if (action === "highlight") {
    restoreSelectionRange();
    document.execCommand("hiliteColor", false, "#fff1a8");
    hideSelectionMenu();
    setFeedback("已高亮选中文本。", "success");
    return;
  }

  const prompts = {
    explain: `请解释这段论文内容，用更容易理解的语言说明它在论文中的作用：\n\n${text}`,
    translate: `请翻译这段论文内容，并保留关键学术术语：\n\n${text}`,
    comment: `请评论这段论文内容，指出它可能的贡献、假设或局限：\n\n${text}`,
    ask: `我选中了这段论文内容，请围绕它回答我的问题并给出理解建议：\n\n${text}`,
  };

  hideSelectionMenu();
  await submitAssistantPrompt(prompts[action] || prompts.ask, false);
}

function renderReaderPanel() {
  if (!readerPanel) return;
  const paper = getSelectedPaper();
  if (!paper) {
    readerPanel.innerHTML = "从左侧文献库选择一篇论文后，这里会展示完整阅读视图。";
    return;
  }

  updateReaderPageIndicator(paper);

  if (titleInput) titleInput.value = paper.title || "";
  if (authorsInput) authorsInput.value = paper.authors || "";
  if (yearInput) yearInput.value = paper.year || "";
  if (sourceInput) sourceInput.value = paper.source || "";
  if (abstractInput) abstractInput.value = paper.abstract || "";
  if (contentInput) contentInput.value = paper.content || "";

  const bodyHtml = renderPaperBody(paper.content || "");
  const keywords = getPaperKeywords(paper);
  const abstractText = getReadableAbstract(paper);
  const figuresHtml = renderFigureGallery(paper);

  readerPanel.innerHTML = `
    <div class="moonlight-page">
      <p class="doc-topline">- 1 - ${escapeHtml(paper.source || "ScholarFlow Imported Paper")} ${paper.year ? escapeHtml(paper.year) : ""}</p>
      <h2 class="moonlight-title">${escapeHtml(paper.title)}</h2>
      ${renderPaperMetaGrid(paper, keywords)}
      <section class="doc-abstract-block">
        <h3 class="doc-abstract-title">摘要</h3>
        <p class="doc-abstract">${escapeHtml(abstractText)}</p>
      </section>
      ${
        pdfPreviewUrl
          ? `<section class="doc-pdf-preview">
              <div class="doc-pdf-preview-head">
                <h3>原始 PDF 预览</h3>
                <a href="${escapeHtml(pdfPreviewUrl)}" target="_blank" rel="noreferrer">新窗口打开</a>
              </div>
              <iframe src="${escapeHtml(pdfPreviewUrl)}#toolbar=0&navpanes=0" title="原始 PDF 预览"></iframe>
            </section>`
          : figuresHtml
      }
      <h3 class="doc-body-title">引言与正文</h3>
      <div class="doc-body-columns">
        ${
          bodyHtml
            ? bodyHtml
            : `<p class="doc-paragraph">当前还没有完整正文。你可以上传 PDF，系统会自动抽取全文；也可以在左侧手动粘贴正文片段。</p>`
        }
      </div>
      ${
        paper.downloaded_pdf_url
          ? `<div class="doc-actions"><a class="button button--ghost" href="${paper.downloaded_pdf_url}" target="_blank" rel="noreferrer">打开原始 PDF</a></div>`
          : ""
      }
    </div>
  `;
  applyReaderZoom();
}

async function boot() {
  await refreshStatus();
  await refreshDashboard();
  renderSearchSummary();
  renderSearchResults();
  if (translationSwitch) toggleTranslationPanel(translationVisible);

  searchForm?.addEventListener("submit", handleSearchSubmit);
  pdfInput?.addEventListener("change", handlePdfImport);
  paperForm?.addEventListener("submit", handlePaperSave);
  noteForm?.addEventListener("submit", handleNoteSave);
  planForm?.addEventListener("submit", handlePlanGenerate);
  writingForm?.addEventListener("submit", handleWritingGenerate);
  analyzeButton?.addEventListener("click", analyzeSelectedPaper);
  translateAbstractButton?.addEventListener("click", () => translateSelectedPaper("abstract"));
  translateContentButton?.addEventListener("click", () => translateSelectedPaper("content"));
  translateAbstractMirror?.addEventListener("click", () => translateSelectedPaper("abstract"));
  translateContentMirror?.addEventListener("click", () => translateSelectedPaper("content"));
  sentenceSearchForm?.addEventListener("submit", searchSentences);
  assistantForm?.addEventListener("submit", sendAssistantMessage);
  demoPaperButton?.addEventListener("click", fillDemoPaper);
  zoomOutButton?.addEventListener("click", () => {
    readerZoom = Math.max(0.78, Number((readerZoom - 0.08).toFixed(2)));
    applyReaderZoom();
  });
  zoomInButton?.addEventListener("click", () => {
    readerZoom = Math.min(1.28, Number((readerZoom + 0.08).toFixed(2)));
    applyReaderZoom();
  });
  translationSwitch?.addEventListener("click", () => toggleTranslationPanel());
  readerPanel?.addEventListener("mouseup", () => window.setTimeout(updateSelectionMenu, 0));
  readerPanel?.addEventListener("keyup", () => window.setTimeout(updateSelectionMenu, 0));
  readerPanel?.addEventListener("scroll", hideSelectionMenu);
  selectionMenu?.addEventListener("mousedown", (event) => event.preventDefault());
  selectionMenu?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-selection-action]");
    if (!button) return;
    handleSelectionAction(button.dataset.selectionAction);
  });
  document.addEventListener("mousedown", (event) => {
    if (selectionMenu?.contains(event.target) || readerPanel?.contains(event.target)) return;
    hideSelectionMenu();
  });
  document.querySelectorAll("[data-reader-tool]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-reader-tool]").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      const tool = button.dataset.readerTool;
      if (tool === "assistant" || tool === "ask") {
        scrollIntoPanel(".assistant-card--chat", "已定位到 AI 提问框。");
        assistantInput?.focus();
      }
      if (tool === "translate") {
        toggleTranslationPanel(true);
        scrollIntoPanel("#translationPanel", "已定位到翻译结果。");
      }
      if (tool === "search") {
        scrollIntoPanel("#sentenceSearchForm", "已定位到单句检索。");
        sentenceQueryInput?.focus();
      }
      if (tool === "top") {
        document.querySelector(".assistant-rail")?.scrollTo({ top: 0, behavior: "smooth" });
        setFeedback("右侧面板已回到顶部。", "success");
      }
    });
  });
}

boot().catch((error) => {
  console.error(error);
});
