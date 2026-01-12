from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from .retriever import Retriever

class RAGState(TypedDict):
    query: str
    documents: List[Dict[str, Any]]
    answer: str
    messages: List[BaseMessage]

def create_rag_graph(
    retriever: Retriever,
    llm: Any,
    prompt_template: Optional[str] = None
):
    """
    创建 RAG 工作流图
    
    Args:
        retriever: 检索器实例
        llm: LLM 实例 (LangChain Runnable)
        prompt_template: 提示词模板
        
    Returns:
        CompiledStateGraph: 编译后的状态图
    """
    
    # 1. 定义节点函数
    
    async def retrieve_node(state: RAGState):
        """检索节点"""
        query = state["query"]
        docs = await retriever.retrieve(query)
        return {"documents": docs}
    
    async def generate_node(state: RAGState):
        """生成节点"""
        query = state["query"]
        docs = state["documents"]
        
        # 格式化文档上下文
        context = "\n\n".join([
            f"Document {i+1}:\n{doc.get('page_content', doc.get('document', ''))}" 
            for i, doc in enumerate(docs)
        ])
        
        # 默认提示词
        default_template = """Based on the following context, please answer the question.
        
Context:
{context}

Question: 
{question}

Answer:"""
        
        template = prompt_template or default_template
        prompt = ChatPromptTemplate.from_template(template)
        
        chain = prompt | llm | StrOutputParser()
        
        response = await chain.ainvoke({
            "context": context,
            "question": query
        })
        
        return {"answer": response}

    # 2. 构建图
    workflow = StateGraph(RAGState)
    
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    
    workflow.set_entry_point("retrieve")
    
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()
