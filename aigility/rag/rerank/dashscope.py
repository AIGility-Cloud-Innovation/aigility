# DashScope Rerank 适配器
"""
DashScope Rerank 适配器 (阿里云百炼 qwen3-rerank)

使用前需要安装: pip install "aigility[rerank-dashscope]"
"""

from typing import List, Optional, TYPE_CHECKING

from ..._optional import import_optional
from .base import BaseRerankAdapter

if TYPE_CHECKING:
    from aigility.rag.config import RerankConfig


class DashScopeRerankAdapter(BaseRerankAdapter):
    """DashScope Rerank 适配器"""

    def __init__(self, config: "RerankConfig"):
        super().__init__()
        self._dashscope = import_optional(
            "dashscope",
            feature="DashScope rerank",
            extra="rerank-dashscope",
        )

        self.config = config
        self.model_name = config.model_name
        self.api_key = config.get_api_key()

        if not self.api_key:
            raise ValueError(
                "未配置 DashScope API Key，请设置 DASHSCOPE_API_KEY 环境变量 "
                "或在 RerankConfig 中传入 api_key"
            )

    @classmethod
    def load(cls, config: "RerankConfig") -> "DashScopeRerankAdapter":
        return cls(config)

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
    ) -> List[dict]:
        """
        对文档进行重排序

        Args:
            query: 查询文本
            documents: 待排序的文档内容列表
            top_n: 返回前 N 个结果

        Returns:
            [{"index": int, "relevance_score": float}, ...]
            按 relevance_score 降序排列
        """
        if not documents:
            return []

        n = top_n if top_n is not None else len(documents)

        resp = self._dashscope.TextReRank.call(
            model=self.model_name,
            query=query,
            documents=documents,
            top_n=n,
            api_key=self.api_key,
        )

        if resp.status_code != 200:
            raise Exception(f"DashScope Rerank Error: {resp.message}")

        results = resp.output["results"]
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        if hasattr(resp, 'usage') and resp.usage:
            from ..usage_tracking import TokenUsage
            self._last_usage = TokenUsage(
                total_tokens=getattr(resp.usage, 'total_tokens', 0),
                model=self.model_name,
            )

        return results


__all__ = ["DashScopeRerankAdapter"]
