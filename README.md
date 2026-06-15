# ScholarFlow

ScholarFlow 是一个 AI 辅助论文阅读训练系统。和普通"AI 帮你读论文"不同，它不替代阅读，而是把论文阅读拆成五关闯关，让学生在回答问题、接受纠错的过程中真正读懂论文。

## 核心工作流

```text
研究方向检索 → 候选论文筛选 → PDF 阅读 → AI 精读 → 闯关问答纠错 → 笔记沉淀 → 课堂汇报
```

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端框架 | FastAPI |
| 请求校验 | Pydantic v2 |
| AI 服务 | DeepSeek API |
| 学术检索 | arXiv API |
| PDF 解析 | pypdf |
| 数据存储 | JSON 文件 |
| 环境管理 | python-dotenv |
| Web 服务器 | uvicorn |
| 前端 | HTML / CSS / JavaScript |

## 启动方式

```powershell
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env（首次使用）
# 在项目根目录创建 .env 文件：
# DEEPSEEK_API_KEY=你的API Key
# DEEPSEEK_MODEL=deepseek-v4-flash
# FLASK_DEBUG=1

# 3. 启动服务
python run.py
```

浏览器打开：

- 应用首页：`http://127.0.0.1:5000`
- API 文档（Swagger UI）：`http://127.0.0.1:5000/docs`

## 测试

运行全部自动化测试（93 个）：

```powershell
python -m unittest discover -s tests -v
```

测试覆盖：

- **API 接口测试**（52 个）：覆盖 26 个 API 端点的正常响应和错误处理
- **服务层边界测试**（40 个）：覆盖 fallback 降级、异常输入、分数归一化等边界情况
- **业务逻辑测试**（6 个）：闯关流程、笔记来源保存、示例论文幂等导入

手动测试用例见 [手动测试用例文档](docs/MANUAL_TEST_CASES.md)。

## 项目文档

- [项目文档](docs/PROJECT_DOCUMENTATION.md) — 架构、模块、数据模型、API 接口
- [答辩讲解文档](docs/DEFENSE_PRESENTATION.md) — 技术栈、架构设计、测试技术、话术参考
- [测试文档](docs/TEST_DOCUMENTATION.md) — 测试方法、测试用例、验收清单
- [手动测试用例](docs/MANUAL_TEST_CASES.md) — 36 个手动测试步骤
- [技术栈改进建议](docs/TECH_STACK_AND_TEST_IMPROVEMENT.md) — 后续升级路线图
