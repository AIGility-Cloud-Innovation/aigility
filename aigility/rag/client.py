"""
太忆 (TimeM) RAG 云服务客户端

用于调用太忆 RAG 服务的 HTTP 客户端
"""

import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from ..http.client import HTTPClient


class SearchQuery(BaseModel):
    """搜索查询参数"""
    query: str


class SearchResult(BaseModel):
    """搜索结果"""
    document: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """搜索响应"""
    status: str
    data: List[SearchResult]


class TimeMRAGClient:
    """
    太忆 (TimeM) RAG 云服务客户端

    封装对太忆 RAG API 的调用，包括文件上传、搜索、统计等功能
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
    ):
        """
        初始化太忆 RAG 云服务客户端

        Args:
            base_url: 太忆 RAG 服务的基础 URL (例如: https://api.timem.cloud)
            api_key: 太忆 API 密钥
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

        # 使用 HTTP 客户端
        self.http_client = HTTPClient(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    async def search(
        self,
        query: str,
        kb_id: str
    ) -> str:
        """
        搜索知识库

        Args:
            query: 搜索查询文本
            kb_id: 知识库ID（必填）

        Returns:
            格式化的搜索结果字符串

        Raises:
            Exception: 搜索失败时抛出异常
        """
        try:
            payload = {
                "kb_id": kb_id,
                "query": query,

            }

            response = await self.http_client.request(
                method="POST",
                endpoint="/api/v1/knowledge/search",
                data=payload
            )

            # 解析响应（根据服务端 SearchResponse 格式）
            # 服务端返回格式: {"code": 200, "message": "success", "data": {"results": [...], "total_results": N}}
            if response.get("code") == 200 and response.get("message") == "success":
                data = response.get("data", {})
                results = data.get("results", [])
                total_results = data.get("total_results", 0)

                if total_results == 0 or not results:
                    return f"未找到关于 '{query}' 的相关信息。"

                # 格式化搜索结果
                formatted_results = []
                for idx, result in enumerate(results, 1):
                    text = result.get("text", "")
                    score = result.get("score", 0.0)
                    chunk_id = result.get("chunk_id", "")
                    metadata = result.get("metadata", {})

                    # 构建结果条目
                    result_entry = f"[结果 {idx}] (相关度: {score:.2f})"
                    if chunk_id:
                        result_entry += f" [ID: {chunk_id[:8]}...]"
                    result_entry += f"\n{text}"

                    # 如果有元数据，添加到结果中
                    if metadata:
                        source = metadata.get("source", "")
                        if source:
                            result_entry += f"\n  来源: {source}"

                    formatted_results.append(result_entry)

                return "\n\n".join(formatted_results)
            else:
                return f"搜索失败: {response.get('message', '未知错误')}"

        except Exception as e:
            return f"搜索出错: {str(e)}"

    def search_sync(
        self,
        query: str,
        kb_id: str
    ) -> str:
        """
        同步搜索知识库

        Args:
            query: 搜索查询文本
            kb_id: 知识库ID（必填）

        Returns:
            格式化的搜索结果字符串
        """
        import concurrent.futures
        import threading

        def run_in_new_loop():
            """在新的事件循环中运行异步函数"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.search(query, kb_id)
                )
            finally:
                loop.close()

        try:
            # 尝试获取当前事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已经在事件循环中运行（如 FastAPI 环境）
                    # 在新线程中运行，使用新的事件循环
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_in_new_loop)
                        return future.result(timeout=self.timeout + 5)
                else:
                    # 没有运行中的事件循环，直接使用 asyncio.run
                    return asyncio.run(
                        self.search(query, kb_id)
                    )
            except RuntimeError:
                # 无法获取事件循环，创建新的
                return run_in_new_loop()

        except Exception as e:
            return f"搜索出错: {str(e)}"

    async def upload_file(
        self,
        file_path: str,
        metadata: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上传文件到知识库

        Args:
            file_path: 文件路径
            metadata: JSON 格式的元数据（可选）

        Returns:
            上传结果字典
        """
        # 注意：文件上传需要处理 multipart/form-data
        # 这里简化处理，实际使用时可能需要特殊的实现
        raise NotImplementedError("文件上传功能需要特殊处理，请直接使用 RAG API")

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息字典
        """
        try:
            response = await self.http_client.request(
                method="GET",
                endpoint="/api/v1/knowledge/stats"
            )
            return response
        except Exception as e:
            return {"error": str(e)}

    async def clear_knowledge_base(self) -> Dict[str, Any]:
        """
        清空知识库

        Returns:
            操作结果字典
        """
        try:
            response = await self.http_client.request(
                method="DELETE",
                endpoint="/api/v1/knowledge/clear"
            )
            return response
        except Exception as e:
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            服务是否健康
        """
        try:
            response = await self.http_client.request(
                method="GET",
                endpoint="/api/v1/knowledge/health"
            )
            return response.get("status") == "healthy"
        except Exception:
            return False

    async def close(self):
        """关闭客户端"""
        await self.http_client.close()


def create_timem_rag_client(
    base_url: str,
    api_key: str,
    timeout: float = 30.0
) -> TimeMRAGClient:
    """
    创建太忆 RAG 云服务客户端的工厂函数

    Args:
        base_url: 太忆 RAG 服务的基础 URL
        api_key: 太忆 API 密钥
        timeout: 请求超时时间（秒）

    Returns:
        TimeMRAGClient 实例
    """
    return TimeMRAGClient(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout
    )
