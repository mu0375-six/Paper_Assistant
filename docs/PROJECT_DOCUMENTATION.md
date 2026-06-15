# ScholarFlow 项目文档

## 1. 项目概述

### 1.1 项目名称

ScholarFlow / Paper Assistant

### 1.2 项目定位

ScholarFlow 是一个面向学生和初级研究者的 AI 辅助论文阅读与学习训练系统。项目目标不是简单地让 AI 代替用户总结论文，而是帮助用户完成一套可复用的学术阅读流程：

```text
研究方向检索 → 候选论文筛选 → PDF 阅读 → AI 精读 → 闯关问答纠错 → 笔记沉淀 → 课堂汇报
```

### 1.3 核心价值

- 提供新手阅读路线，降低论文阅读门槛
- 引导用户分步骤理解论文，避免"摘要复述 = 读懂论文"
- 通过闯关问答暴露理解缺口，AI 纠错沉淀为学习记录
- 将 AI 纠错结果转化为笔记和课堂汇报材料

## 2. 技术架构

### 2.1 技术栈总览

| 层级 | 技术 | 说明 |
|---|---|---|
| 后端框架 | **FastAPI** | 自动生成 Swagger 文档、Pydantic 请求校验、原生 async 支持 |
| 请求校验 | **Pydantic** | RequiredStr 自动拒绝空字符串和纯空格，422 返回校验错误 |
| AI 服务 | **DeepSeek API** | deepseek-v4-flash 模型，JSON 模式输出 |
| PDF 解析 | **pypdf** | 文本抽取、图片提取、元数据猜测 |
| 学术检索 | **arXiv API** | 无需 API Key，实时检索真实论文 |
| 数据存储 | **JSON 文件** | 轻量本地存储，零配置启动 |
| 环境管理 | **python-dotenv** | 自动加载 .env，无需手动设置环境变量 |
| Web 服务器 | **uvicorn** | ASGI 生产级服务器 |
| 前端 | **HTML / CSS / JavaScript** | 原生实现，无框架依赖 |

### 2.2 系统架构图

```text
浏览器页面 (HTML/CSS/JS)
    │
    │ HTTP / JSON
    ▼
FastAPI 路由层 (app/main.py)
    │
    │ Pydantic 请求校验 + HTTPException 错误处理
    ▼
ScholarService 业务服务层 (app/scholar_service.py)
    │
    ├── DiscoveryMixin   检索与发现
    ├── PaperMixin       论文管理、PDF、精读、翻译、问答
    ├── ChallengeMixin   闯关训练、评分、课堂汇报
    └── WritingMixin     研究计划、写作包
    │
    ├── DeepSeekClient   AI 模型调用（含降级 fallback）
    ├── JsonStore        本地 JSON 数据读写
    └── arXiv API        学术论文实时检索
```

### 2.3 前端页面

| 页面 | 文件 | 说明 |
|---|---|---|
| 首页 | `web/home.html` | 项目入口、最近文献、最近检索 |
| 研究检索 | `web/discovery.html` | 输入研究方向，展示候选论文 |
| 阅读台 | `web/reader.html` | PDF 阅读、AI 精读、闯关、问答、笔记 |
| 笔记写作 | `web/workspace.html` | 阅读笔记、研究计划、写作草稿 |

## 3. 后端服务模块详解

后端采用 **Mixin 组合模式**，将原来 1400+ 行的单文件拆分为按职责划分的四个模块，由 `ScholarService` 继承组合，对外接口统一不变。

### 3.1 DiscoveryMixin — 检索与发现

**职责**：帮用户找到相关论文，是整个系统的入口。

| 能力 | 说明 |
|---|---|
| arXiv 实时检索 | 调用 arXiv API 获取真实论文，无需 API Key |
| 中文→英文查询翻译 | 用户输入"多模态智能体"，自动转成 `multimodal agent` 去查 arXiv，内置 60+ 中英关键词映射 |
| 降级策略 | arXiv 请求失败时，回退到内置的 8 篇经典论文目录，按关键词匹配排序 |
| 检索历史 | 每次搜索自动保存，支持按 history_id 恢复完整搜索结果 |
| 论文导入 | 把检索结果（含 PDF 下载、文本提取）一键转为文献库中的论文 |

**对外方法**：`search_topic()` / `restore_search_history()` / `translate_candidate()` / `import_catalog_result()` / `download_external_pdf()`

### 3.2 PaperMixin — 论文管理

**职责**：论文全生命周期——创建、PDF 处理、AI 精读、翻译、句子检索、AI 问答、笔记。是最大的模块。

| 能力 | 说明 |
|---|---|
| 论文 CRUD | 创建/更新/获取，自动补全阅读内容（内容不足 1500 字时生成扩展阅读稿） |
| PDF 处理 | 上传 PDF → pypdf 提取文本 → 猜测标题/作者/年份/摘要 → 抽取图片 → 保存到本地 |
| AI 精读 | 调用 DeepSeek 分析论文，返回摘要、关键词、研究问题、方法、发现、局限、阅读问题；API 不可用时走 fallback |
| 翻译 | 按 scope（标题/摘要/全文）翻译论文，结果缓存到论文记录中 |
| 句子检索 | 在论文全文中按关键词匹配句子，支持中英文混合分词 |
| AI 问答 | 基于论文上下文 + 聊天历史回答问题，附带追问建议 |
| 笔记 | 保存阅读笔记，支持 AI 生成笔记和 PDF 选区来源标注 |
| 教程示例论文 | 首次使用时自动创建内置教学论文 |

**对外方法**：`dashboard()` / `get_paper()` / `create_paper()` / `extract_pdf()` / `import_pdf()` / `analyze_paper()` / `translate_paper()` / `sentence_search()` / `assistant_chat()` / `save_note()` / `ensure_sample_paper()`

### 3.3 ChallengeMixin — 闯关训练

**职责**：把论文阅读变成可练习、可评分、可汇报的五关闯关。

| 能力 | 说明 |
|---|---|
| 五关结构 | 问题识别 → 方法流程 → 图表证据 → 局限分析 → 延伸问题，每关有独立的 prompt 和评分标准 |
| AI 评分 | 提交答案后 DeepSeek 按严格教练角色打分（0-100）+ 中文反馈 + 修正答案 + 证据提示 + 下一步任务 |
| 分数归一化 | 模型有时返回 0-1 的小数，自动乘 100；分数与 level 矛盾时自动修正 |
| Fallback 评分 | API 不可用时，基于答案长度 + 关键词匹配 + 阶段相关短语计算规则分数（35-92 分） |
| 课堂汇报 | 汇总五关最佳答案，计算总分，判断是否可以用于课堂汇报，列出优势和待改进项 |

**对外方法**：`get_challenge()` / `submit_challenge_answer()` / `challenge_report()`

### 3.4 WritingMixin — 写作与研究计划

**职责**：把阅读成果转化为写作产出。

| 能力 | 说明 |
|---|---|
| 研究计划 | 输入主题 + 已选论文 → 生成研究主题总结、周计划（含具体任务）、阅读路线、输出目标 |
| 写作包 | 输入主题 + 已选论文 + 笔记 + 写作目标 → 生成大纲、摘要草稿、相关工作草稿、写作建议 |
| 上下文构建 | 自动把论文的分析结果和笔记内容格式化为 LLM 提示词 |
| 降级策略 | API 不可用时，基于模板 + 已有论文标题生成简化版计划和写作包 |

**对外方法**：`build_research_plan()` / `generate_writing_pack()`

### 3.5 模块间依赖关系

```text
DiscoveryMixin  →  PaperMixin.create_paper()    检索结果导入论文库
PaperMixin      →  ChallengeMixin.get_paper()    闯关需要读论文内容
PaperMixin      →  WritingMixin（通过 store）     写作需要论文分析和笔记
```

四个 Mixin 通过 `ScholarService` 继承组合，共享 `self.store` 和 `self.llm_client`，互相通过 `self` 调用方法，对外只需一个 `ScholarService` 实例。

### 3.6 辅助模块

| 文件 | 职责 |
|---|---|
| `app/services/constants.py` | AI 提示词、闯关阶段定义、内置检索目录、arXiv 关键词映射 |
| `app/services/helpers.py` | 纯工具函数（不依赖 store/llm_client）：fallback 生成、PDF 元信息猜测、分词、内容生成等 |
| `app/schemas.py` | Pydantic 请求模型，用于 FastAPI 路由的自动校验 |
| `app/deepseek_client.py` | DeepSeek API 封装，支持 JSON 模式和文本模式 |
| `app/storage.py` | JSON 文件读写，支持 7 种数据实体 |

## 4. AI 降级策略

所有依赖 LLM 的功能都实现了 **fallback 降级**，确保 API 不可用时系统仍能正常运行：

| 功能 | LLM 可用时 | LLM 不可用时（Fallback） |
|---|---|---|
| AI 精读 | DeepSeek 返回结构化分析 | 基于摘要和标题生成简易分析 |
| 闯关评分 | DeepSeek 按 0-100 评分 + 中文反馈 | 基于答案长度 + 关键词匹配规则评分 |
| 翻译 | DeepSeek 双语翻译 | 直接返回原文 |
| AI 问答 | DeepSeek 基于上下文回答 | 基于已有分析生成引导式回答 |
| 研究计划 | DeepSeek 生成周计划和阅读路线 | 基于模板 + 论文标题生成简易计划 |
| 写作包 | DeepSeek 生成大纲和草稿 | 基于模板生成四段式结构 |
| 检索引导 | DeepSeek 提取检索关键词 | 基于中英文分词提取关键词 |

## 5. 数据模型

### Paper

| 字段 | 说明 |
|---|---|
| `id` | 文献唯一 ID |
| `title` | 标题 |
| `authors` | 作者 |
| `year` | 年份 |
| `source` | 来源 |
| `abstract` | 摘要 |
| `content` | 抽取正文 |
| `pages` | 按页抽取文本 |
| `figures` | 抽取图片信息 |
| `downloaded_pdf_url` | 本地 PDF 地址 |
| `analysis` | AI 精读结果 |
| `translations` | 翻译缓存 |
| `tutorial_sample` | 是否为内置示例论文 |

### ChallengeRun

| 字段 | 说明 |
|---|---|
| `paper_id` | 关联论文 |
| `stages` | 5 个闯关阶段 |
| `attempts` | 每关回答历史 |
| `score` | AI 评分 |
| `feedback` | AI 反馈 |
| `correction` | 参考修正 |
| `evidence_hint` | 证据提示 |

### Note

| 字段 | 说明 |
|---|---|
| `paper_id` | 关联论文 |
| `title` | 笔记标题 |
| `content` | 笔记内容 |
| `kind` | 来源类型，如 selection、assistant |
| `source_text` | 原始选区或 AI 回答来源 |
| `page_label` | 页码 |
| `ai_prompt` | AI 问答提示词 |

## 6. API 接口一览

FastAPI 自动生成 Swagger UI，启动后访问 `http://localhost:5000/docs` 即可查看和测试全部 26 个 API 端点。

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/status` | GET | 系统状态（API 配置、统计数据） |
| `/api/dashboard` | GET | 仪表盘数据 |
| `/api/papers` | POST | 创建论文 |
| `/api/papers/{id}` | GET | 获取论文 |
| `/api/papers/import-pdf` | POST | 上传 PDF 导入论文 |
| `/api/tutorial/sample-paper` | POST | 导入示例论文 |
| `/api/papers/{id}/analyze` | POST | AI 精读 |
| `/api/papers/{id}/translate` | POST | 翻译论文 |
| `/api/papers/{id}/sentence-search` | POST | 句子检索 |
| `/api/papers/{id}/assistant` | POST | AI 问答 |
| `/api/papers/{id}/challenge` | GET | 获取闯关 |
| `/api/papers/{id}/challenge/{stage}` | POST | 提交闯关答案 |
| `/api/papers/{id}/challenge-report` | GET | 课堂汇报 |
| `/api/notes` | POST | 保存笔记 |
| `/api/discovery/search` | POST | 研究方向检索 |
| `/api/discovery/history/{id}` | GET | 恢复检索历史 |
| `/api/discovery/translate-result` | POST | 翻译检索结果 |
| `/api/discovery/download-pdf` | POST | 下载 PDF |
| `/api/discovery/save-result` | POST | 保存检索结果到文献库 |
| `/api/research-plan` | POST | 生成研究计划 |
| `/api/writing-pack` | POST | 生成写作包 |

## 7. 错误处理策略

| 错误类型 | HTTP 状态码 | 说明 |
|---|---|---|
| 请求参数校验失败 | **422** | Pydantic 自动校验，返回缺失字段和类型错误详情 |
| 论文/历史不存在 | **404** | ValueError → HTTPException，返回资源未找到 |
| PDF 导入失败 | **500** | 返回错误原因 |
| AI 服务异常 | 不返回错误码 | 自动降级到 fallback，用户无感知 |

## 8. 启动方式

```powershell
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env（首次使用）
# 创建 .env 文件，填入：
# DEEPSEEK_API_KEY=你的API Key
# DEEPSEEK_MODEL=deepseek-v4-flash
# FLASK_DEBUG=1

# 3. 启动服务
python run.py
```

浏览器打开 `http://127.0.0.1:5000`，API 文档在 `http://127.0.0.1:5000/docs`。

## 9. 核心业务流程

### 9.1 新手第一次使用流程

```text
打开阅读台
  → 查看新手教程
  → 导入示例论文
  → 点击 AI 精读
  → 查看摘要和关键词
  → 进入闯关
  → 回答研究问题
  → 查看评分纠错
  → 保存笔记
  → 生成课堂汇报
```

### 9.2 AI 闯关流程

| 关卡 | 训练能力 | 用户任务 |
|---|---|---|
| 第 1 关 | 问题识别 | 说明论文想解决什么问题 |
| 第 2 关 | 方法理解 | 按输入、步骤、输出拆解方法 |
| 第 3 关 | 证据判断 | 解释图表证明了什么和不能证明什么 |
| 第 4 关 | 批判思维 | 指出局限和适用边界 |
| 第 5 关 | 研究延展 | 提出后续研究问题 |
