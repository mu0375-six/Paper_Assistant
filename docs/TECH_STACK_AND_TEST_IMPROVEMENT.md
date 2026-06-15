# ScholarFlow 技术栈与测试体系改进建议

## 1. 文档目的

本文档用于补充 ScholarFlow / Paper Assistant 后续改进方向，重点回答两个问题：

1. 在已有项目文档、测试文档、路线图和验收清单基础上，还可以补充哪些测试与工程交付物。
2. 当前技术栈是否需要升级，以及应按什么优先级升级。

结论先行：

- 当前技术栈适合课程实验和本地演示，不建议在临近验收时大规模迁移框架。
- 更推荐优先增强测试自动化、代码质量检查、配置管理和 AI 输出校验。
- 如果后续作为作品集项目继续完善，可以逐步引入 SQLite、SQLAlchemy、Pydantic、Playwright、Docker 等工程化能力。

---

## 2. 当前项目基础评价

当前项目已经具备课程验收所需的基本完整形态：

- 有可运行的 Flask 后端。
- 有原生 HTML / CSS / JavaScript 前端页面。
- 有 DeepSeek API 接入。
- 有 PDF 解析能力。
- 有本地 JSON 数据存储。
- 有单元测试。
- 有 README、项目文档、测试文档、路线图和验收清单。
- 有 GitHub Actions CI，可自动运行 Python 测试和 JavaScript 语法检查。

因此，当前项目的问题已经不是“缺少基本交付物”，而是：

> 文档中规划的测试方法和工程化措施，还没有全部转化为可自动运行的测试与检查流程。

后续改进应围绕“让测试真正跑起来、让工程质量可证明、让 AI 输出更稳定”展开。

---

## 3. 还可以补充的测试与文档

### 3.1 增加 Flask API 自动化测试

当前测试主要集中在服务层业务逻辑。建议新增接口测试文件：

```text
tests/test_api_routes.py
```

建议覆盖的接口包括：

| 编号 | 接口 | 测试点 | 预期结果 |
| --- | --- | --- | --- |
| API-01 | `/api/status` | 获取系统状态 | 返回 200，包含模型配置和统计信息 |
| API-02 | `/api/dashboard` | 获取仪表盘数据 | 返回 papers、notes、history 等字段 |
| API-03 | `/api/discovery/search` | 空 topic | 返回 400 |
| API-04 | `/api/papers` | 空 title | 返回 400 |
| API-05 | `/api/tutorial/sample-paper` | 导入示例论文 | 返回示例论文对象 |
| API-06 | `/api/papers/<id>/challenge` | 获取闯关 | 返回 5 个关卡 |
| API-07 | `/api/papers/<id>/challenge/<stage>` | 空答案 | 返回 400 |
| API-08 | `/api/notes` | 缺少 paper_id | 返回 400 |

价值：

- 让测试从“函数层”扩展到“接口层”。
- 能证明前后端交互所依赖的 API 具有基本可靠性。
- 更符合软件测试课程中的接口测试要求。

---

### 3.2 增加测试覆盖率报告

建议引入：

```text
coverage
```

本地运行命令：

```powershell
coverage run -m unittest discover -s tests
coverage report -m
```

或者如果后续升级到 pytest：

```powershell
pytest -v --cov=app --cov-report=term-missing
```

CI 中也可以增加覆盖率步骤。课程验收时可以展示覆盖率结果截图。

价值：

- 让测试结果可量化。
- 能说明哪些模块已覆盖、哪些模块仍是风险点。
- 比单纯展示“Ran 6 tests OK”更有说服力。

---

### 3.3 增加端到端测试

当前项目适合增加一条核心 E2E 测试，不必一开始覆盖所有页面。

推荐使用：

```text
Playwright
```

推荐测试路径：

```text
打开 /reader
  -> 导入示例论文
  -> 确认论文进入列表
  -> 点击 AI 精读
  -> 进入闯关
  -> 提交第 1 关答案
  -> 查看评分反馈
```

建议新增：

```text
tests/e2e/test_reader_flow.spec.js
```

价值：

- 证明真实用户流程可以跑通。
- 适合课堂展示。
- 能覆盖前端、后端、数据存储之间的集成问题。

---

### 3.4 增加缺陷记录表

建议新增：

```text
docs/DEFECT_LOG.md
```

示例内容：

| 缺陷编号 | 模块 | 现象 | 严重程度 | 修复方式 | 状态 |
| --- | --- | --- | --- | --- | --- |
| BUG-001 | 闯关评分 | 模型返回 1 分导致显示过低 | 中 | 增加分数归一化 | 已修复 |
| BUG-002 | 笔记保存 | AI 回答来源字段丢失 | 中 | 保存 assistant_message_id 和 ai_prompt | 已修复 |
| BUG-003 | 示例论文 | 重复导入产生重复数据 | 低 | 保证示例论文幂等 | 已修复 |

价值：

- 能体现“发现问题 -> 定位问题 -> 修复问题 -> 回归测试”的测试闭环。
- 软件测试课程中，缺陷管理通常是重要评分点。

---

### 3.5 增加需求-测试追踪矩阵

建议新增：

```text
docs/TRACEABILITY_MATRIX.md
```

示例内容：

| 需求编号 | 需求名称 | 对应用例 | 自动化状态 |
| --- | --- | --- | --- |
| FR-02 | 示例论文 | UT-01、UT-02、API-03 | 已自动化部分 |
| FR-07 | AI 闯关 | UT-03、UT-04、FT-23、API-06 | 已自动化部分 |
| FR-08 | 评分纠错 | UT-05、ET-06 | 已自动化部分 |
| FR-10 | 笔记写作 | UT-07、UT-08、API-08 | 已自动化部分 |
| FR-11 | 研究检索 | API-03、FT-xx | 待自动化 |

价值：

- 能证明需求都有对应测试。
- 方便答辩时说明测试覆盖关系。
- 比单独罗列测试用例更专业。

---

## 4. 技术栈改进建议

当前技术栈：

```text
Flask + 原生 HTML/CSS/JavaScript + JSON 文件存储 + DeepSeek API + pypdf
```

该技术栈适合课程实验，原因是：

- 依赖少，容易运行。
- 不需要复杂部署。
- 老师可以快速复现。
- 项目结构容易解释。
- 本地 JSON 存储便于查看数据。

但如果继续提升工程化程度，可以分阶段升级。

---

## 5. 推荐升级路线

### 5.1 第一阶段：不改变主体技术栈，增强工程质量

这是当前最推荐的路线，风险最低，收益最高。

#### 5.1.1 从 unittest 逐步升级到 pytest

建议引入：

```text
pytest
pytest-cov
```

优势：

- 测试代码更简洁。
- fixture 更适合管理临时目录、测试客户端、FakeLLM。
- 覆盖率集成更方便。
- 输出更适合 CI 展示。

推荐命令：

```powershell
pytest -v --cov=app --cov-report=term-missing
```

如果时间紧，可以先保留 unittest，再用 pytest 兼容运行现有测试。

---

#### 5.1.2 增加 Ruff 代码质量检查

建议引入：

```text
ruff
```

CI 中增加：

```yaml
- name: Lint Python
  run: ruff check app tests
```

价值：

- 自动发现未使用导入、简单代码风格问题和潜在错误。
- 运行速度快，配置成本低。
- 能提升项目工程规范感。

---

#### 5.1.3 增加 python-dotenv 和 .env.example

当前环境变量需要手动在 PowerShell 中设置。建议引入：

```text
python-dotenv
```

新增：

```text
.env.example
```

示例：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-v4-flash
FLASK_DEBUG=1
```

注意：

- `.env` 应加入 `.gitignore`。
- `.env.example` 可以提交到 GitHub。
- 不要把真实 API Key 提交到仓库。

价值：

- 降低启动配置成本。
- 更符合常见 Web 项目规范。
- 方便老师或同学复现。

---

#### 5.1.4 使用 Pydantic 校验 AI 输出

当前项目大量依赖模型返回 JSON。建议引入：

```text
pydantic
```

例如对闯关评分定义结构：

```python
class ChallengeEvaluation(BaseModel):
    score: int
    level: Literal["needs_work", "pass", "strong"]
    feedback: str
    correction: str
    evidence_hint: str
    next_task: str
```

价值：

- 模型返回缺字段时能及时发现。
- 模型返回字段类型错误时能触发 fallback 或重试。
- 提升 AI 功能稳定性。
- 测试断言更明确。

这是 AI 项目中非常值得做的改进。

---

### 5.2 第二阶段：适度工程化升级

如果课程验收时间比较充足，可以考虑以下升级。

#### 5.2.1 JSON 文件存储升级为 SQLite

当前 JSON 文件存储适合 MVP，但存在一些工程限制：

- 并发写入可能覆盖。
- 查询能力弱。
- 数据关系不清晰。
- 缺少唯一约束和字段约束。

推荐升级为：

```text
SQLite + SQLAlchemy
```

建议数据表：

```text
papers
notes
search_history
challenge_runs
assistant_messages
research_plans
writing_drafts
```

价值：

- 保持本地轻量，不需要安装独立数据库。
- 可以展示数据库设计和 ER 图。
- 数据查询和统计更方便。
- 工程化程度明显提高。

风险：

- 会改动存储层和部分业务逻辑。
- 临近验收时不建议贸然迁移。

---

#### 5.2.2 增加请求体验证层

可以使用：

```text
Pydantic
```

或：

```text
Marshmallow
```

用于校验请求体，例如创建论文、保存笔记、提交闯关答案等。

价值：

- 减少路由层手工校验代码。
- 接口错误更统一。
- 方便接口测试。

---

#### 5.2.3 自动生成 API 文档

可以考虑：

```text
flasgger
apispec
```

价值：

- 生成 Swagger / OpenAPI 页面。
- 答辩时可以展示接口设计。
- 对接口测试也有帮助。

该项不是必须，优先级低于 API 测试和覆盖率。

---

#### 5.2.4 前端 JavaScript 模块化

当前前端可以继续使用原生 JS，但建议拆分文件：

```text
web/js/api.js
web/js/state.js
web/js/discovery.js
web/js/reader.js
web/js/workspace.js
web/js/utils.js
```

价值：

- 降低 `app.js` 文件复杂度。
- 方便定位页面逻辑。
- 不需要引入 Vue / React，也能提升可维护性。

---

### 5.3 第三阶段：完整工程化升级

如果后续把项目作为作品集或毕业设计继续做，可以考虑完整升级：

```text
后端：FastAPI
数据库：SQLite / PostgreSQL
ORM：SQLAlchemy / SQLModel
前端：Vue 3 / React
构建工具：Vite
测试：pytest + Playwright
质量检查：Ruff + Black
部署：Docker
CI：GitHub Actions
```

优点：

- 前后端分离更清晰。
- API 文档自动生成。
- 类型校验能力更强。
- 更接近现代 Web 工程项目。

缺点：

- 迁移成本高。
- 容易引入新问题。
- 对当前课程验收来说性价比不一定高。

建议：

> 临近课程验收时，不建议把 Flask 改成 FastAPI，也不建议马上把原生前端改成 Vue / React。当前更应该补测试、补工程质量检查、补功能闭环。

---

## 6. 功能增强建议

除了技术栈升级，还可以补充以下功能，让项目更像真正的学术阅读工具。

### 6.1 引用导出

支持：

- BibTeX 导出。
- RIS 导出。
- GB/T 7714 引用格式。

价值：

- 与论文阅读场景高度相关。
- 实现成本不高。
- 课程展示时容易说明实用性。

---

### 6.2 论文标签和阅读状态

给论文增加标签和状态：

```text
未读 / 阅读中 / 已精读 / 已汇报
```

标签示例：

```text
NLP、LLM、RAG、教育技术、方法论
```

价值：

- 增强文献管理能力。
- 让系统不仅是 AI 总结工具，也像轻量文献库。

---

### 6.3 基于证据的 AI 回答

让 AI 回答返回证据来源：

```json
{
  "answer": "回答内容",
  "evidence": [
    {
      "page": "第 2 页",
      "quote": "论文原文片段"
    }
  ],
  "followups": ["后续问题 1", "后续问题 2"]
}
```

价值：

- 降低 AI 幻觉风险。
- 更符合学术阅读场景。
- 方便用户回到原文核查。

---

### 6.4 错题本和能力画像

基于 5 个闯关维度生成学习画像：

```text
研究问题识别
方法理解
证据判断
批判性思维
研究延展
```

功能包括：

- 保存低分答案。
- 保存 AI 修正建议。
- 显示薄弱能力维度。
- 生成阅读能力雷达图或柱状图。

价值：

- 把项目从“AI 总结工具”升级成“论文阅读训练系统”。
- 是当前项目最有特色的增强方向之一。

---

### 6.5 Markdown 汇报导出

课堂汇报可以增加：

- 一键复制 Markdown。
- 导出 `.md` 文件。
- 独立汇报页面。
- 后续可配合 Marp 转换为 PPT。

价值：

- 强化最终输出。
- 适合课堂展示。
- 与项目定位高度一致。

---

### 6.6 接入真实论文 API

当前检索功能偏演示性质。后续可接入：

- arXiv API。
- Crossref API。
- OpenAlex API。
- Semantic Scholar API。

推荐优先级：

1. arXiv API：门槛低，适合快速实现。
2. Crossref API：适合补充 DOI 和出版信息。
3. OpenAlex API：适合更丰富的学术元数据。
4. Semantic Scholar API：适合补充引用、摘要和相关论文。

价值：

- 提升真实检索能力。
- 让项目从演示数据走向实际学术数据。

---

## 7. 推荐优先级

如果目标是课程验收拿高分，推荐顺序如下：

| 优先级 | 改进项 | 原因 |
| --- | --- | --- |
| 1 | 增加 Flask API 自动化测试 | 最符合软件测试课程要求 |
| 2 | 增加 coverage 覆盖率报告 | 测试结果可量化 |
| 3 | CI 加入 coverage 和 Ruff | 展示自动化质量保障 |
| 4 | 增加一条 Playwright E2E 测试 | 证明真实用户流程可运行 |
| 5 | 增加 DEFECT_LOG.md | 展示缺陷管理过程 |
| 6 | 增加 TRACEABILITY_MATRIX.md | 展示需求与测试对应关系 |
| 7 | 增加 Markdown 汇报导出 | 强化课堂展示价值 |
| 8 | 增加错题本或能力画像 | 强化学习训练特色 |
| 9 | 接入真实论文 API | 提升实用性 |
| 10 | JSON 存储升级 SQLite | 工程化增强，但改动较大 |

如果目标是作品集项目，推荐顺序如下：

| 优先级 | 改进项 | 原因 |
| --- | --- | --- |
| 1 | 拆分 `scholar_service.py` | 降低后端维护复杂度 |
| 2 | 前端 JS 模块化 | 降低前端维护复杂度 |
| 3 | 引入 Pydantic | 稳定 AI JSON 输出和请求校验 |
| 4 | SQLite + SQLAlchemy | 提升数据层工程化 |
| 5 | Playwright E2E | 增强真实流程保障 |
| 6 | Docker 化 | 方便部署和复现 |
| 7 | 接入 arXiv / Crossref / OpenAlex | 提升真实学术检索能力 |
| 8 | 迁移 Vue / React | 长期可维护性更好，但不是当前刚需 |
| 9 | 迁移 FastAPI | 适合长期重构，不建议验收前进行 |

---

## 8. 最终建议

当前 ScholarFlow 的技术栈不需要马上大改。对课程实验来说，最合理的策略是：

```text
保留 Flask 和原生前端
  -> 补 API 测试
  -> 补覆盖率报告
  -> 补 E2E 测试
  -> 加 Ruff / pytest / dotenv / Pydantic
  -> 再考虑 SQLite 和前端模块化
```

这样既能保证项目稳定，又能明显提升软件测试课程的契合度。

一句话总结：

> 当前项目已经具备课程验收基础，下一步不应盲目升级框架，而应优先把测试体系自动化、把 AI 输出结构化、把工程质量检查流程化。这样比直接迁移到 FastAPI 或 Vue / React 更稳，也更容易在课程答辩中体现价值。
