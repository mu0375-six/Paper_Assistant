# ScholarFlow

ScholarFlow 是一个面向学习与学术场景的轻量工作台，围绕四条主线组织：

- 按研究方向检索候选论文
- 把候选论文加入文献库并完成阅读分析
- 记录阅读笔记和知识整理
- 生成研究计划与学术写作草稿

## 当前版本能力

当前 MVP 重点是把学术工作流串起来，而不是直接做高风险的站点爬取：

- 输入研究方向后，系统会生成检索关键词、筛选建议和平台跳转链接
- 页面内会展示一组开放获取或可继续人工检索的候选论文
- 你可以一键把候选论文加入文献库，再继续做阅读分析和笔记
- 支持上传 PDF 自动提取标题、作者、年份、摘要和正文片段
- 自动保留检索历史，方便回看你之前搜过哪些方向

## 技术栈

- Python 3.10+
- Flask
- Requests
- pypdf
- HTML / CSS / JavaScript
- JSON 文件存储

## 启动方式

```powershell
cd "D:\软件测试技术\ScholarFlow"
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
.\.venv\Scripts\python.exe run.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

## 推荐演示流程

1. 输入研究方向，先跑一次“研究方向检索台”
2. 观察关键词建议、筛选重点和候选论文结果
3. 把 1 到 2 篇候选论文加入文献库
4. 对其中一篇生成阅读分析
5. 记录一条阅读笔记
6. 再生成研究计划和写作草稿

## 测试

运行全部自动化测试：

```powershell
python -m unittest discover -s tests -v
```

当前测试覆盖：

- **API 接口测试**（`test_api_routes.py`）：覆盖 status、dashboard、论文 CRUD、AI 精读、闯关、笔记、检索、研究计划、写作包等接口的正常响应和错误处理
- **服务层边界测试**（`test_service_edge_cases.py`）：覆盖 fallback 降级、缺失数据异常、输入校验、分数归一化、空数据仪表盘、笔记默认值等边界情况
- **业务逻辑测试**（`test_challenge_flow.py`、`test_notes_sources.py`、`test_tutorial_sample.py`）：覆盖闯关流程、笔记来源保存、示例论文幂等导入

手动测试用例见 [手动测试用例文档](docs/MANUAL_TEST_CASES.md)。

## 项目文档

- [手动测试用例](docs/MANUAL_TEST_CASES.md)
- [技术栈与测试改进建议](docs/TECH_STACK_AND_TEST_IMPROVEMENT.md)

## 后续可扩展方向

- 接入开放学术 API，如 OpenAlex、Crossref、Semantic Scholar
- 在用户授权前提下增强数据库跳转与馆藏访问
- 支持文献标签、收藏、对比表与引用导出
- 支持 PDF 上传后自动触发阅读分析
