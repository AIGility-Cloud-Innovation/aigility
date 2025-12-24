import os
import sys
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import uuid
from typing import List, Literal, Any,Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel as LangchainBaseModel, Field as LangchainField

current_file_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录（aigility-master）
root_dir = os.path.abspath(os.path.join(current_file_dir, "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    
from aigility.chat.schema import ChatRequest, ChatResponse
from aigility.chat_flow.services.chat_flow_service import ChatFlowService
from aigility.chat_flow.schema import LLMConfig

from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig, IngestionConfig

class ChatService:
    """
    Chat 模块的服务层，负责处理聊天请求，并调用 ChatFlowService。
    """
    def __init__(self, llm_config: LLMConfig = LLMConfig(),rag_config: Optional[RAGConfig] = None,use_rag: Literal["on", "off", "auto"] = "off"):
        # 初始化 LLM 配置
        self.llm_config = llm_config
        self.llm = self.llm_config.get_client()
        
        
        self.rag_config = rag_config if rag_config else RAGConfig()
        print(f"🔧 ChatService 初始化 RAG: Embedding={self.rag_config.embedding.provider}, Store={self.rag_config.vector_store.provider}")
        
        self.rag_service = RAGService(config=self.rag_config)
        # 初始化 ChatFlowService，注入 LLM 配置和 RAG 配置
        self.chat_flow_service = ChatFlowService(llm_config=self.llm_config,rag_service=self.rag_service,use_rag=use_rag )
        
    def add_knowledge(self, file_path: str):
        """
        向知识库添加文件。
        该方法会委托给 RAGService 处理文件的加载、切分和向量化存储。
        """
        
        print(f"📚 正在向知识库添加文件: {file_path}")
        try:
            # 调用底层 RAG 服务的入库逻辑
            self.rag_service.add_file(file_path)
            print("✅ 文件添加成功。")
        except Exception as e:
            print(f"❌ 文件添加失败: {e}")
    def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理聊天请求，调用 LangGraph ChatFlow。
        
        Args:
            request: 包含用户输入和会话ID的请求对象。
            
        Returns:
            包含 AI 回复、建议和流程信息的响应对象。
        """
        session_id = request.session_id if request.session_id else str(uuid.uuid4())
        
        # 模拟历史记录的获取（当前版本简化为只处理当前请求）
        # 在实际应用中，这里会从数据库或缓存中加载历史消息
        history = [] 
        
        # 调用 ChatFlowService
        flow_result = self.chat_flow_service.invoke(
            user_input=request.user_input,
            history=history
        )
        
         # --- 后处理结果解析 ---
        
        # 1. 解析 Tool 调用结果
        tool_results_list = []
        if flow_result.get("tool_results"):
            for tr in flow_result["tool_results"]:
                tool_results_list.append({
                    "tool_name": tr.tool_name,
                    "result": tr.result
                })
        
        # 2. 解析回复建议 (如果 Flow 中生成了建议字符串)
        reply_suggestions = []
        if flow_result.get("reply_suggestions"):
            raw_suggestions = flow_result.get("reply_suggestions")
            if isinstance(raw_suggestions, str):
                reply_suggestions = [s.strip() for s in raw_suggestions.split(',') if s.strip()]
            elif isinstance(raw_suggestions, list):
                reply_suggestions = raw_suggestions
        
        # 格式化工具结果
        tool_results_list = []
        if flow_result.get("tool_results"):
            for tr in flow_result["tool_results"]:
                tool_results_list.append({
                    "tool_name": tr.tool_name,
                    "result": tr.result
                })
        
        # 独立调用标题和建议生成方法
        session_title = self.generate_session_title(request.user_input, flow_result["response"])
        reply_suggestions = self.generate_reply_suggestions(flow_result["response"])

        # 构建 ChatResponse
        response = ChatResponse(
            response=flow_result["response"],
            session_id=session_id,
            session_title=session_title,
            reply_suggestions=reply_suggestions,
            thought_process=flow_result.get("thought_process"),
            tool_results=tool_results_list
        )
        
        return response

    # --- 独立服务：生成会话标题 ---

    def generate_session_title(self, user_input: str, ai_response: str) -> str:
        """
        即插即用的独立方法：根据对话内容生成会话标题。
        """
        class TitleOutput(LangchainBaseModel):
            title: str = LangchainField(description="A concise session title (max 15 characters).")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的标题生成器。请根据用户输入和AI回复，生成一个简洁的会话标题（不超过15个字）。"),
            ("human", f"用户输入: {user_input}\nAI回复: {ai_response}")
        ])
        
        chain = prompt | self.llm.with_structured_output(TitleOutput)
        
        try:
            result = chain.invoke({})
            return result.title
        except Exception as e:
            print(f"Title generation failed: {e}")
            return "新会话"

    # --- 独立服务：生成回复建议 ---

    def generate_reply_suggestions(self, ai_response: str) -> List[str]:
        """
        即插即用的独立方法：根据 AI 回复生成后续回复建议。
        """
        class SuggestionOutput(LangchainBaseModel):
            suggestions: List[str] = LangchainField(description="A list of 3 suggested follow-up questions or actions.")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的建议生成器。请根据AI的回复，生成3个用户可能感兴趣的后续问题或操作建议。"),
            ("human", f"AI回复: {ai_response}")
        ])
        
        chain = prompt | self.llm.with_structured_output(SuggestionOutput)
        
        try:
            result = chain.invoke({})
            return result.suggestions
        except Exception as e:
            print(f"Suggestion generation failed: {e}")
            return ["请重试", "报告错误"]
        
# ==========================================
# 集成测试入口
# ==========================================
if __name__ == "__main__":
    print("🚀 启动 ChatService 集成测试... 【测试 rag 状态为on：总是执行 RAG】")

    # --- 1. 配置准备 ---
    # 模拟用户根据 `config.py` 的结构自定义配置
    
    # A. 嵌入模型配置 (例如使用 DashScope/通义千问 兼容模式)
    # 也可以设为 provider="huggingface", model_name="BAAI/bge-small-zh-v1.5"
    my_embedding_config = EmbeddingConfig(
        provider="huggingface", 
        model_name="BAAI/bge-small-zh-v1.5",
        # kwargs={"device": "cpu"} # 如果有 GPU 可以传 cuda
    )

    # B. 向量库配置 (使用 Chroma 本地存储)
    my_vector_store_config = VectorStoreConfig(
        provider="chroma",
        collection_name="demo_kb",
        persist_path="./chroma_db"
    )

    # C. 数据处理配置 (自定义切分大小)
    my_ingestion_config = IngestionConfig(
        chunk_size=300,        # 测试用，设小一点方便观察
        chunk_overlap=50,
        enable_text_cleaning=True
    )

    # D. 总配置
    my_rag_config = RAGConfig(
        embedding=my_embedding_config,
        vector_store=my_vector_store_config,
        ingestion=my_ingestion_config,
        search_top_k=5 # 只召回最相似的5条
    )

    # --- 2. 实例化服务 ---
    # 假设我们用 DashScope 作为 LLM
    my_llm_config = LLMConfig(
        provider="dashscope", 
        model_name="qwen3-max", # 使用这一轮对话的 LLM
        api_key=os.getenv("DASHSCOPE_API_KEY") 
    )
    
    # 初始化 ChatService
    agent = ChatService(llm_config=my_llm_config, rag_config=my_rag_config,use_rag="on")

    # --- 3. 准备测试数据 ---
    test_file = "test.pdf"
    # --- 4. 执行数据入库 ---
    print("\n--- [Step 1] 灌入知识库 ---")
    agent.add_knowledge(test_file)

    # --- 5. 执行对话 ---
    print("\n--- [Step 2] 发起对话 ---")
    question = "面试一般考察什么"
    req = ChatRequest(user_input=question)
    
    result = agent.process_chat(req)

    # --- 6. 展示结果 ---
    print("\n" + "="*60)
    print(f"❓ 用户问题: {question}")
    print("-" * 60)
    
    # 打印思考过程 (CoT)
    if result.thought_process:
        print(f"🧠 思考过程:\n{result.thought_process}")
    
    print("-" * 60)
    
    # 打印工具调用结果 (验证 RAG 是否生效)
    if result.tool_results:
        print(f"🛠️ 工具调用结果:")
        for tool_res in result.tool_results:
            print(f"  [{tool_res['tool_name']}] -> {tool_res['result']}")
    else:
        print("⚠️ 未触发工具调用 (可能直接回答了或 LLM 判断不需要)")
        
    print("-" * 60)
    print(f"🤖 最终回复:\n{result.response}")
    print("="*60)

    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)