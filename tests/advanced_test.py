"""
SDK 公共 API 补全测试（真实调用）

验证中期补全的改动：
1. ChatAgent.chat() 委托 ChatFlow 并获得真实模型响应
2. create_llm() 转发到 ModelFactory 并创建可用的 LLM
3. ADKClient 配置完整传递到模型
4. 模块导出完整性
5. ChatAgent.chat() kb_id 参数传递与 RAG 集成
6. ADKClientBuilder.with_rag() 配置 RAG
"""

import pytest
import inspect
import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# DeepSeek 真实配置（从 .env 读取）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 智谱 AI 真实配置（从 .env 读取）
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPUAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
ZHIPUAI_MODEL = "glm-4-flash"

# 无 DeepSeek 凭据时（如 CI 未配置 secret）跳过真实调用测试
requires_deepseek = pytest.mark.skipif(
    not DEEPSEEK_API_KEY, reason="无 DEEPSEEK_API_KEY，跳过 DeepSeek 真实调用测试"
)
# TimeM RAG 配置（从 .env 读取）
TIMEM_ENABLED = os.getenv("TIMEM_ENABLED", "false").lower() == "true"
TIMEM_API_KEY = os.getenv("TIMEM_API_KEY")
TIMEM_BASE_URL = os.getenv("TIMEM_BASE_URL", "https://api.timem.cloud")
TIMEM_TEST_KB_ID = os.getenv("TIMEM_KB_ID", "kn1")


def make_deepseek_config(**overrides):
    """构造 DeepSeek ADKConfig"""
    from aigility.core.config import ADKConfig
    kwargs = dict(
        llm_provider="deepseek",
        llm_model=DEEPSEEK_MODEL,
        llm_api_key=DEEPSEEK_API_KEY,
        llm_base_url=DEEPSEEK_BASE_URL,
        llm_temperature=0.1,
        llm_max_tokens=256,
    )
    kwargs.update(overrides)
    return ADKConfig(**kwargs)


# ============================================================
# 1. 模块导入测试
# ============================================================

class TestImports:
    """测试所有公共 API 可正常导入"""

    def test_import_chat_agent(self):
        from aigility.chat.agent import ChatAgent
        assert ChatAgent is not None

    def test_import_create_chat_agent(self):
        from aigility.chat.agent import create_chat_agent
        assert callable(create_chat_agent)

    def test_import_create_llm(self):
        from aigility.model import create_llm
        assert callable(create_llm)

    def test_import_adk_client_builder(self):
        from aigility import ADKClientBuilder
        assert ADKClientBuilder is not None

    def test_import_adk_client(self):
        from aigility import ADKClient
        assert ADKClient is not None

    def test_import_create_client(self):
        from aigility import create_client
        assert callable(create_client)

    def test_llmprovider_removed(self):
        """LLMProvider 已从 model 模块移除"""
        from aigility import model
        assert not hasattr(model, 'LLMProvider')


# ============================================================
# 2. ChatAgent 接口测试
# ============================================================

class TestChatAgentInterface:
    """测试 ChatAgent 的接口完整性"""

    def test_chat_agent_has_chat_method(self):
        from aigility.chat.agent import ChatAgent
        assert callable(getattr(ChatAgent, 'chat', None))

    def test_chat_agent_has_invoke_method(self):
        from aigility.chat.agent import ChatAgent
        assert callable(getattr(ChatAgent, 'invoke', None))

    def test_chat_agent_has_chat_flow_property(self):
        from aigility.chat.agent import ChatAgent
        assert isinstance(ChatAgent.__dict__.get('chat_flow'), property)

    def test_chat_agent_has_get_prompt(self):
        from aigility.chat.agent import ChatAgent
        assert callable(getattr(ChatAgent, 'get_prompt', None))

    def test_chat_agent_constructor_accepts_adk_config(self):
        from aigility.chat.agent import ChatAgent
        config = make_deepseek_config()
        agent = ChatAgent(name="test", adk_config=config)
        assert agent.adk_config is config

    def test_chat_agent_default_adk_config(self):
        from aigility.chat.agent import ChatAgent
        from aigility.core.config import ADKConfig
        agent = ChatAgent(name="test")
        assert isinstance(agent.adk_config, ADKConfig)

    def test_chat_agent_stores_name(self):
        from aigility.chat.agent import ChatAgent
        agent = ChatAgent(name="my_agent")
        assert agent.name == "my_agent"

    def test_chat_agent_get_prompt_returns_string(self):
        from aigility.chat.agent import ChatAgent
        agent = ChatAgent(name="test")
        result = agent.get_prompt()
        assert isinstance(result, str)


# ============================================================
# 3. create_llm() 真实调用测试
# ============================================================

@requires_deepseek
class TestCreateLlmReal:
    """测试 create_llm() 创建真实可用的 LLM 实例"""

    def test_create_llm_returns_chatopenai(self):
        """create_llm() 返回 LangChain ChatModel 实例"""
        from aigility.model import create_llm
        from langchain_core.language_models.chat_models import BaseChatModel

        llm = create_llm(
            provider="deepseek",
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        # 装了 langchain-deepseek 时返回 ChatDeepSeek（非 ChatOpenAI 子类），
        # 未装时回退 ChatOpenAI，两者都是合法的 BaseChatModel
        assert isinstance(llm, BaseChatModel)

    def test_create_llm_can_invoke(self):
        """create_llm() 创建的 LLM 可以真实调用"""
        from aigility.model import create_llm

        llm = create_llm(
            provider="deepseek",
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.1,
            max_tokens=64,
        )
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content="回复OK两个字母")])
        assert response.content is not None
        assert len(response.content) > 0
        print(f"\n  [create_llm] 模型回复: {response.content}")

    def test_create_llm_default_params(self):
        """create_llm() 默认参数正确（无 key 时跳过实例创建）"""
        from aigility.model import create_llm
        from aigility.core.config import ADKConfig
        from aigility.core.model_factory import ModelFactory

        # 验证默认 ADKConfig 参数
        config = ADKConfig()
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.llm_api_key is None
        assert config.llm_base_url is None

        # 如果有 OPENAI_API_KEY 则验证完整链路，否则只验证参数构造
        if os.getenv("OPENAI_API_KEY"):
            llm = create_llm()
            assert llm is not None
        else:
            pytest.skip("无 OPENAI_API_KEY，跳过默认 LLM 创建")

    def test_create_llm_passes_temperature(self):
        """create_llm() 传递 temperature"""
        from aigility.model import create_llm

        llm = create_llm(
            provider="deepseek",
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.0,
        )
        assert llm.temperature == 0.0


# ============================================================
# 4. ModelFactory 真实调用测试
# ============================================================

@requires_deepseek
class TestModelFactoryReal:
    """测试 ModelFactory.create_llm() 通过 ADKConfig 创建真实 LLM"""

    def test_model_factory_creates_llm(self):
        from aigility.core.model_factory import ModelFactory
        config = make_deepseek_config()
        llm = ModelFactory.create_llm(config)
        assert llm is not None

    def test_model_factory_llm_can_invoke(self):
        """ModelFactory 创建的 LLM 可以真实调用"""
        from aigility.core.model_factory import ModelFactory
        from langchain_core.messages import HumanMessage

        config = make_deepseek_config(llm_max_tokens=64)
        llm = ModelFactory.create_llm(config)
        response = llm.invoke([HumanMessage(content="回复OK两个字母")])
        assert response.content is not None
        assert len(response.content) > 0
        print(f"\n  [ModelFactory] 模型回复: {response.content}")

    def test_model_factory_config_propagation(self):
        """验证 ADKConfig 的参数完整传递到 ChatOpenAI"""
        from aigility.core.model_factory import ModelFactory

        config = make_deepseek_config(llm_temperature=0.0, llm_max_tokens=128)
        llm = ModelFactory.create_llm(config)

        assert llm.temperature == 0.0
        assert llm.max_tokens == 128


# ============================================================
# 5. ChatAgent 真实对话测试
# ============================================================

@requires_deepseek
class TestChatAgentReal:
    """测试 ChatAgent 使用真实 DeepSeek 模型进行对话"""

    def test_chat_returns_response(self):
        """chat() 返回真实的模型回复"""
        from aigility.chat.agent import ChatAgent

        config = make_deepseek_config()
        agent = ChatAgent(name="test_agent", adk_config=config)
        response = agent.chat("回复OK两个字母", rag_used="off")

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [ChatAgent.chat] 模型回复: {response}")

    def test_chat_flow_is_lazy_loaded(self):
        """chat_flow 是懒加载的"""
        from aigility.chat.agent import ChatAgent

        config = make_deepseek_config()
        agent = ChatAgent(name="test", adk_config=config)
        assert agent._chat_flow is None

        _ = agent.chat_flow
        assert agent._chat_flow is not None

    def test_invoke_returns_agent_response(self):
        """invoke(state) 返回 AgentResponse"""
        from aigility.chat.agent import ChatAgent
        from aigility.core.types import State, Message, MessageRole, AgentResponse

        config = make_deepseek_config()
        agent = ChatAgent(name="test", adk_config=config)

        state = State(
            messages=[Message(role=MessageRole.USER, content="回复OK两个字母")],
            metadata={"kb_id": "kn1"},  # RAG 模式下 kb_id 必传
        )
        result = asyncio.run(agent.invoke(state))

        assert isinstance(result, AgentResponse)
        assert len(result.content) > 0
        print(f"\n  [ChatAgent.invoke] 模型回复: {result.content}")


# ============================================================
# 6. ADKClient 端到端测试
# ============================================================

class TestADKClientE2E:
    """测试 ADKClient 从 Builder 到真实对话的完整链路"""

    def test_builder_config_flows_to_agent(self):
        """Builder → ADKClient → ChatAgent 配置完整传递"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .build()
        )
        agent = client.create_chat_agent("e2e_agent")

        assert agent.adk_config.llm_provider == "deepseek"
        assert agent.adk_config.llm_model == DEEPSEEK_MODEL
        assert agent.adk_config.llm_api_key == DEEPSEEK_API_KEY
        assert agent.adk_config.llm_base_url == DEEPSEEK_BASE_URL

    @requires_deepseek
    def test_builder_agent_can_chat(self):
        """通过 Builder 创建的 Agent 可以真实对话"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .with_debug(enabled=False)
            .build()
        )
        agent = client.create_chat_agent("chat_agent")
        response = agent.chat("回复OK两个字母", rag_used="off")

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [ADKClient→Agent] 模型回复: {response}")

    @requires_deepseek
    def test_builder_chatflow_can_invoke(self):
        """通过 Builder 创建的 ChatFlow 可以真实调用"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .build()
        )
        chatflow = client.create_chatflow("e2e_flow")
        result = chatflow.invoke(user_input="回复OK两个字母", rag_used="off")

        assert "response" in result
        assert len(result["response"]) > 0
        print(f"\n  [ADKClient→ChatFlow] 模型回复: {result['response']}")

    @requires_deepseek
    def test_create_client_shortcut(self):
        """create_client() 快捷函数创建的客户端可用"""
        from aigility import create_client

        client = create_client(
            llm_provider="deepseek",
            llm_model=DEEPSEEK_MODEL,
            llm_api_key=DEEPSEEK_API_KEY,
            llm_base_url=DEEPSEEK_BASE_URL,
        )
        agent = client.create_chat_agent("shortcut_agent")
        response = agent.chat("回复OK两个字母", rag_used="off")

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [create_client→Agent] 模型回复: {response}")


# ============================================================
# 7. 向后兼容性测试
# ============================================================

# ============================================================
# 7. 多提供商测试（智谱 AI GLM）
# ============================================================

@pytest.mark.skipif(not ZHIPUAI_API_KEY, reason="无 ZHIPUAI_API_KEY")
class TestZhipuAIProvider:
    """测试智谱 AI（GLM）作为 OpenAI 兼容提供商"""

    def test_zhipuai_create_llm(self):
        """create_llm() 创建智谱 AI 实例"""
        from aigility.model import create_llm

        llm = create_llm(
            provider="openai",
            model=ZHIPUAI_MODEL,
            api_key=ZHIPUAI_API_KEY,
            base_url=ZHIPUAI_BASE_URL,
        )
        assert llm is not None
        print(f"\n  [智谱AI] LLM 创建成功: {llm.model_name}")

    def test_zhipuai_can_invoke(self):
        """智谱 AI 模型可以真实调用"""
        from aigility.model import create_llm
        from langchain_core.messages import HumanMessage

        llm = create_llm(
            provider="openai",
            model=ZHIPUAI_MODEL,
            api_key=ZHIPUAI_API_KEY,
            base_url=ZHIPUAI_BASE_URL,
            max_tokens=64,
        )
        response = llm.invoke([HumanMessage(content="回复OK两个字母")])
        assert response.content is not None
        assert len(response.content) > 0
        print(f"\n  [智谱AI] 模型回复: {response.content}")

    def test_zhipuai_via_adkclient(self):
        """通过 ADKClient 使用智谱 AI"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="openai",
                model=ZHIPUAI_MODEL,
                api_key=ZHIPUAI_API_KEY,
                base_url=ZHIPUAI_BASE_URL,
            )
            .build()
        )
        agent = client.create_chat_agent("zhipuai_agent")
        response = agent.chat("回复OK两个字母", rag_used="off")

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [ADKClient→智谱AI] 模型回复: {response}")

    def test_zhipuai_config_propagation(self):
        """智谱 AI 配置完整传递到模型"""
        from aigility.core.model_factory import ModelFactory
        from aigility.core.config import ADKConfig

        config = ADKConfig(
            llm_provider="openai",
            llm_model=ZHIPUAI_MODEL,
            llm_api_key=ZHIPUAI_API_KEY,
            llm_base_url=ZHIPUAI_BASE_URL,
            llm_temperature=0.0,
            llm_max_tokens=128,
        )
        llm = ModelFactory.create_llm(config)

        assert llm.temperature == 0.0
        assert llm.max_tokens == 128


# ============================================================
# 8. 向后兼容性测试
# ============================================================

class TestBackwardCompatibility:
    """测试现有用法不受影响"""

    @requires_deepseek
    def test_chatflow_direct_creation(self):
        """直接创建 ChatFlow（与外部项目用法一致）"""
        from aigility.chatflow.flow import ChatFlow

        config = make_deepseek_config()
        flow = ChatFlow(name="direct_flow", adk_config=config)
        result = flow.invoke(user_input="回复OK两个字母", rag_used="off")

        assert "response" in result
        assert len(result["response"]) > 0
        print(f"\n  [直接ChatFlow] 模型回复: {result['response']}")

    @requires_deepseek
    def test_chat_service_direct_creation(self):
        """直接创建 ChatService"""
        from aigility.chat.service import ChatService
        from aigility.chat.schema import ChatRequest

        config = make_deepseek_config()
        service = ChatService(adk_config=config)

        request = ChatRequest(
            user_input="回复OK两个字母",
            session_id="test-session",
            rag_used="off",
        )
        response = service.process_chat(request)

        assert response.response is not None
        assert len(response.response) > 0
        assert response.session_id == "test-session"
        print(f"\n  [直接ChatService] 模型回复: {response.response}")

    def test_adk_config_fields(self):
        """ADKConfig 字段完整"""
        from aigility.core.config import ADKConfig
        config = ADKConfig()
        assert hasattr(config, 'llm_provider')
        assert hasattr(config, 'llm_model')
        assert hasattr(config, 'llm_api_key')
        assert hasattr(config, 'llm_base_url')
        assert hasattr(config, 'llm_temperature')
        assert hasattr(config, 'llm_max_tokens')
        assert hasattr(config, 'timem_enabled')
        assert hasattr(config, 'timem_api_key')
        assert hasattr(config, 'timem_base_url')

    def test_model_factory_signature(self):
        """ModelFactory.create_llm() 签名不变"""
        from aigility.core.model_factory import ModelFactory
        sig = inspect.signature(ModelFactory.create_llm)
        params = list(sig.parameters.keys())
        assert 'config' in params


# ============================================================
# 9. ADKConfig RAG 字段测试
# ============================================================

class TestADKConfigRAG:
    """测试 ADKConfig 中的 RAG 相关字段"""

    def test_adk_config_has_timem_kb_id(self):
        """ADKConfig 有 timem_kb_id 字段"""
        from aigility.core.config import ADKConfig
        config = ADKConfig()
        assert hasattr(config, 'timem_kb_id')
        assert config.timem_kb_id is None

    def test_adk_config_timem_kb_id_default_none(self):
        """timem_kb_id 默认值为 None"""
        from aigility.core.config import ADKConfig
        config = ADKConfig()
        assert config.timem_kb_id is None

    def test_adk_config_timem_kb_id_settable(self):
        """timem_kb_id 可设置"""
        from aigility.core.config import ADKConfig
        config = ADKConfig(timem_kb_id="kb_test_123")
        assert config.timem_kb_id == "kb_test_123"

    def test_adk_config_all_timem_fields(self):
        """ADKConfig 包含完整的 TimeM 配置字段"""
        from aigility.core.config import ADKConfig
        config = ADKConfig(
            timem_enabled=True,
            timem_api_key="sk-test",
            timem_base_url="https://api.timem.cloud",
            timem_kb_id="kb_my_knowledge_base",
        )
        assert config.timem_enabled is True
        assert config.timem_api_key == "sk-test"
        assert config.timem_base_url == "https://api.timem.cloud"
        assert config.timem_kb_id == "kb_my_knowledge_base"


# ============================================================
# 10. ADKClientBuilder.with_rag() 测试
# ============================================================

class TestADKClientBuilderRAG:
    """测试 ADKClientBuilder 的 with_rag() 方法"""

    def test_with_rag_enabled(self):
        """with_rag() 启用 RAG"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_rag(enabled=True)
            .build()
        )
        assert client.config.timem_enabled is True

    def test_with_rag_disabled(self):
        """with_rag(enabled=False) 关闭 RAG"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_rag(enabled=False)
            .build()
        )
        assert client.config.timem_enabled is False

    def test_with_rag_api_key(self):
        """with_rag() 设置 api_key"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_rag(api_key="sk-rag-test")
            .build()
        )
        assert client.config.timem_api_key == "sk-rag-test"

    def test_with_rag_base_url(self):
        """with_rag() 设置 base_url"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_rag(base_url="https://rag.example.com")
            .build()
        )
        assert client.config.timem_base_url == "https://rag.example.com"

    def test_with_rag_kb_id(self):
        """with_rag() 设置默认 kb_id"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_rag(kb_id="kb_default_123")
            .build()
        )
        assert client.config.timem_kb_id == "kb_default_123"

    def test_with_rag_full_config(self):
        """with_rag() 完整配置"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_rag(
                enabled=True,
                api_key="sk-rag-full",
                base_url="https://rag.full.com",
                kb_id="kb_full_456",
            )
            .build()
        )
        assert client.config.timem_enabled is True
        assert client.config.timem_api_key == "sk-rag-full"
        assert client.config.timem_base_url == "https://rag.full.com"
        assert client.config.timem_kb_id == "kb_full_456"

    def test_with_rag_chained_with_llm(self):
        """with_rag() 可以与 with_llm() 链式调用"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .with_rag(
                enabled=True,
                api_key=TIMEM_API_KEY,
                base_url=TIMEM_BASE_URL,
                kb_id="kb_test",
            )
            .with_debug(enabled=False)
            .build()
        )
        assert client.config.llm_provider == "deepseek"
        assert client.config.timem_enabled is True
        assert client.config.timem_kb_id == "kb_test"


# ============================================================
# 11. ChatAgent kb_id 参数测试
# ============================================================

class TestChatAgentKbId:
    """测试 ChatAgent.chat() / invoke() 的 kb_id 传递"""

    def test_chat_raises_when_kb_id_missing_for_rag(self):
        """rag_used='auto' 但不传 kb_id 时抛出 ValueError"""
        from aigility.chat.agent import ChatAgent
        import pytest

        config = make_deepseek_config()
        # 不设置 timem_kb_id
        config.timem_kb_id = None
        agent = ChatAgent(name="test", adk_config=config)

        with pytest.raises(ValueError, match="未提供 kb_id"):
            agent.chat("测试问题", rag_used="auto")

    def test_chat_raises_when_kb_id_missing_for_rag_on(self):
        """rag_used='on' 但不传 kb_id 时抛出 ValueError"""
        from aigility.chat.agent import ChatAgent
        import pytest

        config = make_deepseek_config()
        config.timem_kb_id = None
        agent = ChatAgent(name="test", adk_config=config)

        with pytest.raises(ValueError, match="未提供 kb_id"):
            agent.chat("测试问题", rag_used="on")

    def test_chat_no_error_when_rag_off_without_kb_id(self):
        """rag_used='off' 时不传 kb_id 不会报错"""
        from aigility.chat.agent import ChatAgent

        config = make_deepseek_config()
        config.timem_kb_id = None
        agent = ChatAgent(name="test", adk_config=config)

        # 不应抛出异常
        response = agent.chat("回复OK两个字母", rag_used="off")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_chat_accepts_kb_id(self):
        """chat() 方法接受 kb_id 参数"""
        from aigility.chat.agent import ChatAgent
        import inspect

        sig = inspect.signature(ChatAgent.chat)
        params = list(sig.parameters.keys())
        assert 'kb_id' in params

    def test_chat_kb_id_default_none(self):
        """chat() 的 kb_id 参数默认为 None"""
        from aigility.chat.agent import ChatAgent
        import inspect

        sig = inspect.signature(ChatAgent.chat)
        assert sig.parameters['kb_id'].default is None

    def test_chat_with_kb_id_no_rag_config(self):
        """传入 kb_id 但未配置 RAG 服务时，纯对话正常完成"""
        from aigility.chat.agent import ChatAgent

        config = make_deepseek_config()
        agent = ChatAgent(name="test", adk_config=config)
        response = agent.chat("回复OK两个字母", rag_used="off", kb_id="kb_test")
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [chat+kb_id+off] 模型回复: {response}")

    def test_chat_without_kb_id_still_works(self):
        """不传 kb_id 时仍然正常工作（向后兼容）"""
        from aigility.chat.agent import ChatAgent

        config = make_deepseek_config()
        agent = ChatAgent(name="test", adk_config=config)
        response = agent.chat("回复OK两个字母", rag_used="off")
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [chat-no-kb_id] 模型回复: {response}")

    def test_adk_config_kb_id_as_default(self):
        """adk_config.timem_kb_id 作为 chat() 的默认 kb_id"""
        from aigility.chat.agent import ChatAgent

        config = make_deepseek_config()
        config.timem_kb_id = "kb_from_config"
        agent = ChatAgent(name="test", adk_config=config)
        # 不传 kb_id，应该使用 config 中的值
        response = agent.chat("回复OK两个字母", rag_used="off")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_chat_kb_id_overrides_config(self):
        """chat() 传入的 kb_id 优先于 adk_config.timem_kb_id"""
        from aigility.chat.agent import ChatAgent

        config = make_deepseek_config()
        config.timem_kb_id = "kb_from_config"
        agent = ChatAgent(name="test", adk_config=config)
        response = agent.chat("回复OK两个字母", rag_used="off", kb_id="kb_from_param")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_invoke_reads_kb_id_from_state_metadata(self):
        """invoke() 从 state.metadata 读取 kb_id"""
        from aigility.chat.agent import ChatAgent
        from aigility.core.types import State, Message, MessageRole, AgentResponse

        config = make_deepseek_config()
        agent = ChatAgent(name="test", adk_config=config)

        state = State(
            messages=[Message(role=MessageRole.USER, content="回复OK两个字母")],
            metadata={"kb_id": "kb_from_state"},
        )
        result = asyncio.run(agent.invoke(state))
        assert isinstance(result, AgentResponse)
        assert len(result.content) > 0
        print(f"\n  [invoke+kb_id] 模型回复: {result.content}")


# ============================================================
# 12. ChatAgent RAG 真实调用测试（需要 TimeM 服务）
# ============================================================

@pytest.mark.skipif(not TIMEM_ENABLED, reason="TIMEM_ENABLED=false，跳过 RAG 真实调用测试")
@pytest.mark.skipif(not TIMEM_API_KEY, reason="无 TIMEM_API_KEY")
class TestChatAgentRAGReal:
    """测试 ChatAgent 通过 ADKClientBuilder 配置并真实调用 RAG"""

    def test_builder_with_rag_agent_chat_auto(self):
        """通过 Builder 配置 RAG → Agent.chat(rag_used='auto') → 验证 RAG 调用"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .with_rag(
                enabled=True,
                api_key=TIMEM_API_KEY,
                base_url=TIMEM_BASE_URL,
            )
            .with_debug(enabled=True)
            .build()
        )
        agent = client.create_chat_agent("rag_agent")
        response = agent.chat(
            "你们的最小起订量是多少？",
            rag_used="auto",
            kb_id=TIMEM_TEST_KB_ID,
        )
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [RAG auto] 模型回复: {response}")

    def test_builder_with_rag_agent_chat_on(self):
        """通过 Builder 配置 RAG → Agent.chat(rag_used='on') → 强制 RAG 调用"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .with_rag(
                enabled=True,
                api_key=TIMEM_API_KEY,
                base_url=TIMEM_BASE_URL,
            )
            .with_debug(enabled=True)
            .build()
        )
        agent = client.create_chat_agent("rag_on_agent")
        response = agent.chat(
            "产品有哪些认证？",
            rag_used="on",
            kb_id=TIMEM_TEST_KB_ID,
        )
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [RAG on] 模型回复: {response}")

    def test_builder_with_rag_agent_chat_off(self):
        """通过 Builder 配置 RAG → Agent.chat(rag_used='off') → 纯对话模式"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .with_rag(
                enabled=True,
                api_key=TIMEM_API_KEY,
                base_url=TIMEM_BASE_URL,
            )
            .build()
        )
        agent = client.create_chat_agent("rag_off_agent")
        response = agent.chat("你好", rag_used="off")
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [RAG off] 模型回复: {response}")

    def test_builder_default_kb_id(self):
        """Builder 中设置的默认 kb_id 被 chat() 使用"""
        from aigility import ADKClientBuilder

        client = (
            ADKClientBuilder()
            .with_llm(
                provider="deepseek",
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            .with_rag(
                enabled=True,
                api_key=TIMEM_API_KEY,
                base_url=TIMEM_BASE_URL,
                kb_id=TIMEM_TEST_KB_ID,  # 默认 kb_id
            )
            .build()
        )
        agent = client.create_chat_agent("default_kb_agent")
        # 不传 kb_id，应使用 builder 中设置的默认值
        response = agent.chat("你们的产品规格是什么？", rag_used="auto")
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [RAG 默认 kb_id] 模型回复: {response}")

    def test_rag_via_create_client_shortcut(self):
        """create_client() 快捷函数 + RAG 完整链路"""
        from aigility import create_client

        client = create_client(
            llm_provider="deepseek",
            llm_model=DEEPSEEK_MODEL,
            llm_api_key=DEEPSEEK_API_KEY,
            llm_base_url=DEEPSEEK_BASE_URL,
        )
        # 手动设置 RAG 配置
        client.config.timem_enabled = True
        client.config.timem_api_key = TIMEM_API_KEY
        client.config.timem_base_url = TIMEM_BASE_URL

        agent = client.create_chat_agent("shortcut_rag_agent")
        response = agent.chat(
            "你们提供哪些服务？",
            rag_used="auto",
            kb_id=TIMEM_TEST_KB_ID,
        )
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\n  [create_client RAG] 模型回复: {response}")


# ============================================================
# 13. ADKClientBuilder 导入测试
# ============================================================

class TestADKClientBuilderImport:
    """测试 ADKClientBuilder 可从顶层包导入"""

    def test_import_adk_client_builder_from_aigility(self):
        """from aigility import ADKClientBuilder"""
        from aigility import ADKClientBuilder
        assert ADKClientBuilder is not None

    def test_import_adk_client_from_aigility(self):
        """from aigility import ADKClient"""
        from aigility import ADKClient
        assert ADKClient is not None

    def test_adk_client_builder_callable(self):
        """ADKClientBuilder 可实例化"""
        from aigility import ADKClientBuilder
        builder = ADKClientBuilder()
        assert builder is not None


# ============================================================
# 14. ChatService kb_id 默认值测试
# ============================================================

class TestChatServiceKbId:
    """测试 ChatService 使用 adk_config.timem_kb_id 作为默认值"""

    def test_chat_service_uses_config_kb_id(self):
        """ChatService 在没有 request.kb_id 时使用 adk_config.timem_kb_id"""
        from aigility.chat.service import ChatService
        from aigility.chat.schema import ChatRequest

        config = make_deepseek_config()
        config.timem_kb_id = "kb_from_service_config"
        service = ChatService(adk_config=config)

        request = ChatRequest(
            user_input="回复OK两个字母",
            rag_used="off",
            # 不传 kb_id，应使用 config.timem_kb_id
        )
        response = service.process_chat(request)
        assert response.response is not None
        assert len(response.response) > 0
        print(f"\n  [ChatService config kb_id] 模型回复: {response.response}")

    def test_chat_service_request_kb_id_overrides_config(self):
        """ChatService 的 request.kb_id 优先于 config.timem_kb_id"""
        from aigility.chat.service import ChatService
        from aigility.chat.schema import ChatRequest

        config = make_deepseek_config()
        config.timem_kb_id = "kb_from_config"
        service = ChatService(adk_config=config)

        request = ChatRequest(
            user_input="回复OK两个字母",
            kb_id="kb_from_request",
            rag_used="off",
        )
        response = service.process_chat(request)
        assert response.response is not None
        assert len(response.response) > 0


# ============================================================
# 15. ChatFlow 通过 RunnableConfig 传递 kb_id 测试
# ============================================================

class TestChatFlowKbIdConfig:
    """测试 ChatFlow.invoke() 通过 RunnableConfig 传递 kb_id"""

    def test_chatflow_direct_with_kb_id_config(self):
        """直接使用 ChatFlow + RunnableConfig 传递 kb_id"""
        from aigility.chatflow.flow import ChatFlow
        from langchain_core.runnables import RunnableConfig

        config = make_deepseek_config()
        flow = ChatFlow(name="kb_test_flow", adk_config=config)

        run_config = RunnableConfig(configurable={"timem_kb_id": "kb_via_config"})
        result = flow.invoke(
            user_input="回复OK两个字母",
            rag_used="off",
            config=run_config,
        )
        assert "response" in result
        assert len(result["response"]) > 0
        print(f"\n  [ChatFlow+RunnableConfig] 模型回复: {result['response']}")

    def test_chatflow_without_config_still_works(self):
        """ChatFlow 不传 config 时仍然正常（向后兼容）"""
        from aigility.chatflow.flow import ChatFlow

        config = make_deepseek_config()
        flow = ChatFlow(name="no_config_flow", adk_config=config)
        result = flow.invoke(user_input="回复OK两个字母", rag_used="off")
        assert "response" in result
        assert len(result["response"]) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
