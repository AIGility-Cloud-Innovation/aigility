"""
ADP 服务客户端

用于调用 ADP 提供的远程 Chat Agent 服务。
"""

import json
from typing import Optional, Dict, Any, AsyncGenerator
from ..http.client import HTTPClient, create_http_client


class ADPClient:
    """
    ADP 服务客户端

    用于调用 ADP 提供的远程 Chat Agent 服务。

    注意：RAG 功能请使用 aigility.rag.TimeMRAGClient
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, **kwargs):
        """
        初始化 ADP 客户端

        Args:
            base_url: ADP 服务地址 (e.g. "http://localhost:8000/api/v1")
            api_key: API Key (可选)
            **kwargs: 透传给 HTTPClient 的其他配置
        """
        self.http = create_http_client(base_url=base_url, api_key=api_key, **kwargs)

    async def chat(
        self,
        user_input: str,
        agent: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用远程 Agent 进行对话

        user_id 通过 API Key 由服务端自动获取，无需手动传递。

        Args:
            user_input: 用户输入
            agent: Agent 名称 (e.g. "careerask")
            session_id: 会话 ID

        Returns:
            Dict: 响应数据
        """
        payload = {
            "user_input": user_input,
            "agent": agent,
            "session_id": session_id
        }

        return await self.http.request("POST", "/chat", data=payload)

    async def chat_stream(
        self,
        user_input: str,
        agent: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用远程 Agent 进行流式对话

        user_id 通过 API Key 由服务端自动获取，无需手动传递。

        Args:
            user_input: 用户输入
            agent: Agent 名称 (e.g. "careerask")
            session_id: 会话 ID

        Yields:
            Dict: 流式响应数据
        """
        payload = {
            "user_input": user_input,
            "agent": agent,
            "session_id": session_id,
            "stream": True
        }

        async for line in self.http.stream_request("POST", "/chat", data=payload):
            if line.startswith("data:"):
                try:
                    content = line[len("data:"):].strip()
                    if content:
                        yield json.loads(content)
                except json.JSONDecodeError:
                    # 忽略无法解析的行
                    pass

    async def close(self):
        """关闭客户端"""
        await self.http.close()
