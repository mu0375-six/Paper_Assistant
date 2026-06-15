"""ScholarFlow 核心服务外观。

将原来 1400+ 行的单文件拆分为按职责划分的 Mixin，
由 ScholarService 继承组合，对外接口完全不变。

├── services/constants.py   常量（提示词、闯关阶段、检索目录）
├── services/helpers.py     纯工具函数（不依赖 store/llm_client）
├── services/discovery_mixin.py  检索与发现
├── services/paper_mixin.py      论文管理、PDF、精读、翻译、问答
├── services/challenge_mixin.py  闯关训练、评分、课堂汇报
└── services/writing_mixin.py    研究计划、写作包
"""

from .deepseek_client import DeepSeekClient
from .services.discovery_mixin import DiscoveryMixin
from .services.paper_mixin import PaperMixin
from .services.challenge_mixin import ChallengeMixin
from .services.writing_mixin import WritingMixin
from .storage import JsonStore


class ScholarService(PaperMixin, DiscoveryMixin, ChallengeMixin, WritingMixin):
    """ScholarFlow 统一服务外观。

    通过 Mixin 继承组合各子模块，self.store / self.llm_client
    由 __init__ 设置，供各 Mixin 通过 self 访问。
    """

    def __init__(self, store: JsonStore, llm_client: DeepSeekClient) -> None:
        self.store = store
        self.llm_client = llm_client
