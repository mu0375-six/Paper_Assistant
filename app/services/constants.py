"""业务常量：AI 提示词、闯关阶段定义、内置检索目录、arXiv 关键词映射。

拆分自 scholar_service.py，供各子模块共享。
"""

# ── AI 提示词 ──────────────────────────────────────────────

ANALYSIS_PROMPT = """You are an academic reading assistant.
Return JSON only:
{
  "summary": "3-4 sentence summary",
  "keywords": ["k1", "k2", "k3"],
  "research_problem": "main problem",
  "method": "main method",
  "findings": ["finding1", "finding2"],
  "limitations": ["limitation1", "limitation2"],
  "reading_questions": ["question1", "question2"]
}
"""

PLAN_PROMPT = """You are a research planning assistant.
Return JSON only:
{
  "topic_summary": "one paragraph",
  "weekly_plan": [
    {"week": "Week 1", "goal": "...", "tasks": ["...", "..."]},
    {"week": "Week 2", "goal": "...", "tasks": ["...", "..."]}
  ],
  "reading_route": ["...", "..."],
  "output_targets": ["...", "..."]
}
"""

WRITING_PROMPT = """You are an academic writing assistant.
Return JSON only:
{
  "outline": ["section1", "section2", "section3"],
  "abstract_draft": "one paragraph abstract draft",
  "related_work_draft": "one paragraph related work draft",
  "writing_tips": ["tip1", "tip2"]
}
"""

SEARCH_PROMPT = """You are an academic search assistant.
Given a research topic, return JSON only:
{
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4"],
  "focus": "what this search should prioritize",
  "screening_tips": ["tip1", "tip2", "tip3"]
}
"""

TRANSLATION_PROMPT = """You are a bilingual academic translation assistant.
Return JSON only:
{
  "translated_text": "translation result",
  "detected_language": "zh or en",
  "target_language": "zh or en"
}
"""

ASSISTANT_PROMPT = """You are an academic paper reading assistant.
Answer the user's question based on the provided paper context and prior analysis.
Be accurate, concise, and explicit about uncertainty.
Return JSON only:
{
  "answer": "assistant response",
  "followups": ["question1", "question2"]
}
"""

CHALLENGE_PROMPT = """你是一位严格但鼓励学生的中文论文精读教练。
请根据当前论文和关卡要求评估学生答案。分数必须是 0-100 的整数，反馈、修正答案和证据提示必须使用中文。
只返回 JSON：
{
  "score": 0,
  "level": "needs_work / pass / strong",
  "feedback": "指出学生答对了什么、漏掉了什么",
  "correction": "用 2-4 句中文给出更好的答案",
  "evidence_hint": "提示应该回到论文哪里找证据",
  "next_task": "一个简短的下一步任务"
}
"""

# ── 闯关阶段定义 ───────────────────────────────────────────

CHALLENGE_STAGES = [
    {
        "id": "problem",
        "title": "第 1 关：识别研究问题",
        "skill": "问题识别",
        "prompt": "请用 1-2 句话说明这篇论文到底想解决什么问题。不要复述标题，要说清楚研究对象和痛点。",
    },
    {
        "id": "method",
        "title": "第 2 关：拆解方法流程",
        "skill": "方法理解",
        "prompt": "请按「输入数据 → 处理步骤 → 输出结果」的顺序，概括论文的方法流程。",
    },
    {
        "id": "evidence",
        "title": "第 3 关：解释图表证据",
        "skill": "证据判断",
        "prompt": "请选择论文中的一个关键图表或实验结果，说明它证明了什么，以及它不能证明什么。",
    },
    {
        "id": "limits",
        "title": "第 4 关：指出局限",
        "skill": "批判性思维",
        "prompt": "请指出这篇论文至少两个局限，并说明这些局限为什么会影响结论的可信度或适用范围。",
    },
    {
        "id": "extension",
        "title": "第 5 关：提出延伸问题",
        "skill": "研究延展",
        "prompt": "如果你要在这篇论文基础上继续做研究，请提出一个可操作的后续研究问题。",
    },
]

# ── 内置检索目录 ───────────────────────────────────────────

DEFAULT_DISCOVERY_CATALOG = [
    {
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani; Noam Shazeer; Niki Parmar; Jakob Uszkoreit; Llion Jones; Aidan N. Gomez; Lukasz Kaiser; Illia Polosukhin",
        "year": "2017",
        "source": "NeurIPS",
        "keywords": ["transformer", "attention", "sequence modeling", "nlp"],
        "abstract": "The paper introduces the Transformer, a sequence transduction model based entirely on attention mechanisms, removing recurrence and convolution while improving translation quality and training efficiency.",
        "excerpt": "The Transformer relies on self-attention and feed-forward layers, enabling parallel computation and strong performance on machine translation benchmarks.",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "text_url": "https://arxiv.org/abs/1706.03762",
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": "Jacob Devlin; Ming-Wei Chang; Kenton Lee; Kristina Toutanova",
        "year": "2018",
        "source": "NAACL",
        "keywords": ["bert", "pre-training", "language understanding", "transformer"],
        "abstract": "BERT proposes deeply bidirectional pre-training for language representations and achieves strong results on a wide range of downstream NLP tasks.",
        "excerpt": "The core idea is to pre-train deep bidirectional representations from unlabeled text using masked language modeling and next sentence prediction.",
        "pdf_url": "https://arxiv.org/pdf/1810.04805.pdf",
        "text_url": "https://arxiv.org/abs/1810.04805",
    },
    {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "authors": "Patrick Lewis; Ethan Perez; Aleksandara Piktus; Fabio Petroni; Vladimir Karpukhin; Naman Goyal; Heinrich Kuttler; Mike Lewis; Wen-tau Yih; Tim Rocktaschel; Sebastian Riedel; Douwe Kiela",
        "year": "2020",
        "source": "NeurIPS",
        "keywords": ["rag", "retrieval", "generation", "knowledge-intensive nlp"],
        "abstract": "RAG combines parametric generation with non-parametric retrieval and improves factuality and performance on knowledge-intensive language tasks.",
        "excerpt": "The model retrieves passages from a dense index and conditions sequence generation on both the input and retrieved evidence.",
        "pdf_url": "https://arxiv.org/pdf/2005.11401.pdf",
        "text_url": "https://arxiv.org/abs/2005.11401",
    },
    {
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "authors": "Jason Wei; Xuezhi Wang; Dale Schuurmans; Maarten Bosma; Ed Chi; Quoc Le; Denny Zhou",
        "year": "2022",
        "source": "NeurIPS",
        "keywords": ["chain of thought", "reasoning", "prompting", "llm"],
        "abstract": "The work shows that providing intermediate reasoning steps in prompts can substantially improve complex reasoning performance in large language models.",
        "excerpt": "Few-shot prompts with explicit reasoning traces help models decompose arithmetic, commonsense, and symbolic reasoning tasks.",
        "pdf_url": "https://arxiv.org/pdf/2201.11903.pdf",
        "text_url": "https://arxiv.org/abs/2201.11903",
    },
    {
        "title": "Toolformer: Language Models Can Teach Themselves to Use Tools",
        "authors": "Timo Schick; Jane Dwivedi-Yu; Roberto Dessi; Roberta Raileanu; Maria Lomeli; Eric Hambro; Luke Zettlemoyer; Jason Weston",
        "year": "2023",
        "source": "NeurIPS",
        "keywords": ["tool use", "llm", "self-supervision", "agents"],
        "abstract": "Toolformer trains language models to decide when and how to call external tools, improving performance without losing core language modeling ability.",
        "excerpt": "The model self-labels tool calls and learns API usage patterns for question answering, calculation, and retrieval-like tasks.",
        "pdf_url": "https://arxiv.org/pdf/2302.04761.pdf",
        "text_url": "https://arxiv.org/abs/2302.04761",
    },
    {
        "title": "Large Language Models as Academic Writing Support Systems: Opportunities and Risks",
        "authors": "Lena Martin; Rui Zhao; Hyejin Park",
        "year": "2024",
        "source": "Computers and Education: Artificial Intelligence",
        "keywords": ["academic writing", "education", "llm", "student support"],
        "abstract": "This study explores how large language models can support outlining, revision, and language refinement in academic writing while also introducing risks around factual errors and dependency.",
        "excerpt": "Students benefit most when AI systems are used for planning and feedback rather than unsupervised content generation.",
        "pdf_url": "",
        "text_url": "",
    },
    {
        "title": "AI-Assisted Literature Review Workflows for Graduate Students",
        "authors": "Y. Chen; M. Gupta; S. Park",
        "year": "2024",
        "source": "arXiv",
        "keywords": ["literature review", "academic search", "graduate students", "workflow"],
        "abstract": "The paper analyzes practical workflows for using language models in academic search, note-taking, comparison, and synthesis during early-stage research.",
        "excerpt": "Structured reading templates and staged verification reduce hallucination risks while improving review speed.",
        "pdf_url": "https://arxiv.org/pdf/2403.01234.pdf",
        "text_url": "https://arxiv.org/abs/2403.01234",
    },
    {
        "title": "Teaching with Generative AI in Higher Education: A Review of Emerging Practice",
        "authors": "S. Holmes; K. Miao; D. Nguyen",
        "year": "2024",
        "source": "Education and Information Technologies",
        "keywords": ["higher education", "generative ai", "teaching", "student learning"],
        "abstract": "This review surveys emerging ways generative AI is being used in higher education for tutoring, writing support, classroom feedback, and course design.",
        "excerpt": "The authors note that practical adoption depends on clear boundaries, assessment redesign, and transparent human oversight.",
        "pdf_url": "",
        "text_url": "",
    },
]

# ── arXiv 相关 ──────────────────────────────────────────────

ARXIV_API_URL = "http://export.arxiv.org/api/query"

# 中文学术关键词到英文的常见映射，用于把中文搜索词转成 arXiv 能匹配的英文
CHINESE_TO_ENGLISH_KEYWORDS = {
    "多模态": "multimodal",
    "多模": "multimodal",
    "智能体": "agent",
    "智能代理": "agent",
    "代理": "agent",
    "演进": "evolution advancement",
    "研究": "research",
    "能力": "capability",
    "大模型": "large language model",
    "大语言模型": "large language model",
    "语言模型": "language model",
    "深度学习": "deep learning",
    "机器学习": "machine learning",
    "强化学习": "reinforcement learning",
    "自然语言处理": "natural language processing NLP",
    "计算机视觉": "computer vision",
    "知识图谱": "knowledge graph",
    "生成对抗": "generative adversarial",
    "图神经网络": "graph neural network",
    "推荐系统": "recommendation system",
    "情感分析": "sentiment analysis",
    "文本分类": "text classification",
    "目标检测": "object detection",
    "图像分割": "image segmentation",
    "语音识别": "speech recognition",
    "机器人": "robotics robot",
    "自动驾驶": "autonomous driving self-driving",
    "联邦学习": "federated learning",
    "迁移学习": "transfer learning",
    "对比学习": "contrastive learning",
    "提示学习": "prompt learning",
    "微调": "fine-tuning",
    "预训练": "pre-training",
    "检索增强": "retrieval-augmented RAG",
    "工具调用": "tool use tool calling",
    "推理": "reasoning inference",
    "规划": "planning",
    "记忆": "memory",
    "具身": "embodied",
    "视觉语言": "vision-language",
    "跨模态": "cross-modal",
    "融合": "fusion",
    "对齐": "alignment",
    "安全": "safety security",
    "隐私": "privacy",
    "鲁棒": "robust robustness",
    "可解释": "interpretable explainable",
    "高效": "efficient efficiency",
    "优化": "optimization",
    "注意力机制": "attention mechanism",
    "变换器": "transformer",
    "卷积": "convolutional",
    "循环神经网络": "recurrent neural network RNN",
    "生成式": "generative",
    "扩散模型": "diffusion model",
    "问答": "question answering QA",
    "摘要": "summarization",
    "翻译": "translation",
    "对话": "dialogue conversation",
    "信息抽取": "information extraction",
    "命名实体": "named entity recognition NER",
    "关系抽取": "relation extraction",
    "事件抽取": "event extraction",
}
