"""
RAG Workflow - 基于 LangGraph 的工作流模式 RAG

提供可组合、可可视化的 RAG 工作流，支持检索和生成两个节点的编排。
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class RAGWorkflowState(TypedDict):
    """
    RAG 工作流状态

    Attributes:
        query: 用户查询
        documents: 检索到的文档列表
        answer: 生成的答案
        messages: 消息历史（可选，用于多轮对话）
    """
    query: str
    documents: List[str]
    answer: str
    messages: Optional[List[BaseMessage]]


def create_rag_workflow(
    rag_service,
    llm,
    prompt_template: Optional[str] = None,
    search_top_k: int = 3
):
    """
    创建基于 LangGraph 的 RAG 工作流

    Args:
        rag_service: RAGService 实例（来自 aigility.rag.RAGService）
        llm: LLM 实例 (LangChain Runnable)
        prompt_template: 自定义提示词模板（可选）
        search_top_k: 检索返回的文档数量

    Returns:
        CompiledStateGraph: 编译后的状态图，可通过 workflow.invoke() 调用

    Example:
        >>> from aigility.rag import RAGService, RAGConfig, create_rag_workflow
        >>> from langchain_openai import ChatOpenAI
        >>>
        >>> # 初始化服务
        >>> rag_service = RAGService()
        >>> llm = ChatOpenAI(model="gpt-4")
        >>>
        >>> # 创建工作流
        >>> workflow = create_rag_workflow(rag_service, llm)
        >>>
        >>> # 执行查询
        >>> result = workflow.invoke({
        ...     "query": "什么是机器学习？",
        ...     "messages": []
        ... })
        >>> print(result["answer"])
    """

    # 1. 定义节点函数

    def retrieve_node(state: RAGWorkflowState) -> Dict:
        """
        检索节点：使用 RAGService 进行语义检索

        Args:
            state: 当前工作流状态

        Returns:
            更新后的状态（包含检索到的文档）
        """
        query = state["query"]

        # 使用 RAGService 的 search 方法进行检索
        # RAGService.search() 返回格式化的字符串，包含多个文档切片
        documents_text = rag_service.search(query)

        # 将结果分割成文档列表（按引用标记分割）
        documents = []
        if documents_text:
            # 简单分割：每个 "--- [引用" 开始的段落是一个文档
            doc_blocks = documents_text.split("--- [引用")
            # 跳过第一个空块（如果有）
            documents = [block.strip() for block in doc_blocks[1:] if block.strip()]

        return {"documents": documents}

    def generate_node(state: RAGWorkflowState) -> Dict:
        """
        生成节点：使用 LLM 基于检索到的文档生成答案

        Args:
            state: 当前工作流状态

        Returns:
            更新后的状态（包含生成的答案）
        """
        query = state["query"]
        docs = state.get("documents", [])

        # 格式化文档上下文
        if docs:
            context = "\n\n".join([
                f"[引用 {i+1}]\n{doc}"
                for i, doc in enumerate(docs)
            ])
        else:
            context = "（未检索到相关文档）"

        # 默认提示词模板
        default_template = """你是一个专业的知识问答助手。请基于以下检索到的文档内容回答用户的问题。

注意：
1. 如果文档内容与问题相关，请基于文档内容给出准确、详细的回答
2. 如果文档内容不足以回答问题，请诚实地说明，不要编造信息
3. 引用文档中的关键信息来支持你的回答
4. 保持回答的专业性和准确性

---
检索到的文档：
{context}
---

用户问题：
{question}

请回答："""

        template = prompt_template or default_template
        prompt = ChatPromptTemplate.from_template(template)

        # 构建 LLM 链
        chain = prompt | llm | StrOutputParser()

        # 生成答案
        response = chain.invoke({
            "context": context,
            "question": query
        })

        return {"answer": response}

    # 2. 构建工作流图
    workflow = StateGraph(RAGWorkflowState)

    # 添加节点
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)

    # 设置入口点
    workflow.set_entry_point("retrieve")

    # 添加边（节点之间的连接）
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    # 编译并返回工作流
    return workflow.compile()


__all__ = [
    "create_rag_workflow",
    "RAGWorkflowState",
]
