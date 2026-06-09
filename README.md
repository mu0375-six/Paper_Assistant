# ScholarFlow / Paper Assistant

ScholarFlow 是一个面向学习和课堂汇报场景的 AI 论文阅读助手。它围绕“检索论文、阅读论文、AI 精读、闯关纠错、保存笔记、生成课堂汇报”形成完整学习闭环。

## 主要功能

- 研究方向检索：输入研究方向，生成候选论文、关键词和筛选建议。
- PDF 阅读台：支持上传 PDF、查看原文、文本层选区和选区处理。
- AI 精读：提炼摘要、关键词、研究问题、方法流程和推荐追问。
- 闯关问答：通过 5 个关卡训练论文阅读能力，并获得 AI 纠错评分。
- 新手教程：内置 6 步论文阅读路线、按钮说明和示例论文。
- 笔记写作：保存阅读笔记、AI 回答和课堂汇报素材。

## 技术栈

- Python 3.10+
- Flask
- DeepSeek API
- pypdf
- HTML / CSS / JavaScript
- JSON 文件本地存储

## 快速开始

1. 创建并激活虚拟环境。

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. 安装依赖。

```powershell
pip install -r requirements.txt
```

3. 配置 DeepSeek API。

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
```

4. 启动服务。

```powershell
python run.py
```

5. 浏览器访问。

```text
http://127.0.0.1:5000
```

## 课堂展示建议

1. 打开阅读台，展示“新手教程”。
2. 点击“导入示例论文”，说明系统适合第一次使用者上手。
3. 点击“AI 精读”，展示摘要、关键词和推荐追问。
4. 进入“闯关”，回答研究问题、方法流程、图表证据、局限和延伸问题。
5. 展示 AI 纠错评分和“生成课堂汇报”结果。
6. 保存 AI 回答或选区为笔记，说明系统能沉淀学习记录。

## 测试

```powershell
python -m unittest tests.test_tutorial_sample tests.test_challenge_flow tests.test_notes_sources -v
```

当前测试覆盖：

- 示例论文幂等导入
- AI 闯关评分与课堂汇报
- 分数归一化
- PDF 选区和 AI 回答保存为笔记

## 项目与测试文档

- [项目文档](docs/PROJECT_DOCUMENTATION.md)
- [测试文档](docs/TEST_DOCUMENTATION.md)
- [功能递增开发路线图](docs/ROADMAP.md)
- [课程验收清单](docs/ACCEPTANCE_CHECKLIST.md)

## 下一阶段改进重点

当前阶段暂不升级技术栈，优先提高项目使用效果和验收完整度：

1. 增加错题本，保存低分闯关答案、AI 修正和证据提示。
2. 增加能力画像，用 5 个闯关维度展示论文阅读能力。
3. 增强课堂汇报，支持 Markdown 复制或独立汇报页。
4. 补充 API 测试、异常测试和端到端测试。
5. 在时间允许时接入开放论文 API，提高真实检索能力。

## 目录结构

```text
app/
  __init__.py
  deepseek_client.py
  main.py
  scholar_service.py
  storage.py
web/
  home.html
  discovery.html
  reader.html
  workspace.html
  app.js
  reader-controller.js
  reader-modern.css
  style.css
tests/
  test_challenge_flow.py
  test_notes_sources.py
  test_tutorial_sample.py
run.py
requirements.txt
```

## 注意

- 不要把真实 API Key 提交到 GitHub。
- `data/` 下的 JSON 和下载文件是本地运行数据，默认不提交。
- 本项目使用 Flask 开发服务器，适合课程演示和本地运行。
