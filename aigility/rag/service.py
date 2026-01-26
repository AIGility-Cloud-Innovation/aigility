# rag_service.py
# [服务层] 对外暴露的统一入口 (RAGService)

import os
import sys
import shutil
import hashlib
import logging
from typing import Optional, Dict, List

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 抑制 tokenizers 并行警告
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# 处理直接运行时的导入问题
try:
    # 作为包导入时使用相对导入
    from .config import RAGConfig
    from .embeddings.factory import EmbeddingFactory
    from .vector_stores.factory import VectorStoreFactory
    from .ingestion import IngestionManager
except ImportError:
    # 直接运行时使用绝对导入
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _package_dir = os.path.dirname(os.path.dirname(_current_dir))
    if _package_dir not in sys.path:
        sys.path.insert(0, _package_dir)
    
    from aigility.rag.config import RAGConfig
    from aigility.rag.embeddings.factory import EmbeddingFactory
    from aigility.rag.vector_stores.factory import VectorStoreFactory
    from aigility.rag.ingestion import IngestionManager

# NLP 依赖用于提取元数据 (关键词/摘要)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import jieba
    HAS_NLP_DEPS = True
except ImportError:
    HAS_NLP_DEPS = False


class RAGService:
    """RAG 服务主类，提供文档入库和检索能力"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """
        初始化 RAG 服务
        Args:
            config: RAG 配置对象。如果不传，使用默认配置。
        """
        self.config = config or RAGConfig()
        
        logging.info(f"🔧 Initializing RAG with: Embedding={self.config.embedding.provider}, Store={self.config.vector_store.provider}")

        # 1. 初始化 Embedding 模型
        self.embedding_model = EmbeddingFactory.get_embedding_model(self.config.embedding)
        
        # 2. 初始化 Vector Store (注入 embedding)
        self.vector_store = VectorStoreFactory.get_vector_store(
            self.config.vector_store, 
            self.embedding_model
        )
        
        # 3. 初始化数据处理模块 (核心解析逻辑在此)
        self.ingestion = IngestionManager(self.config.ingestion)
        
        # 4. 文档元信息存储 (内存缓存，生产环境建议持久化到 SQLite/MySQL)
        self.doc_meta_info: Dict[str, dict] = {}
        self.global_doc_keywords: List[str] = []

    def _generate_meta_from_chunks(self, chunks: List, doc_name: str) -> dict:
        """
        基于处理好的 Chunks 反向生成文档元信息
        优势：Chunks 已经包含了清洗后的表格 Markdown 和 Excel 键值对，关键词提取更准确。
        """
        if not chunks:
            return {}

        # 聚合前 N 个 Chunk 的内容作为摘要依据 (避免全文拼接太长)
        # 假设前 5000 个字符包含核心信息
        combined_text = "\n".join([c.page_content for c in chunks[:10]])
        
        # 生成摘要 (简单截取)
        doc_summary = combined_text[:300].replace("\n", " ").strip() + "..."

        # 生成关键词
        doc_keywords = []
        if HAS_NLP_DEPS:
            try:
                # 简单清洗
                clean_text = combined_text.replace("\n", " ").replace("|", " ").replace("-", " ")
                word_list = jieba.lcut(clean_text)
                seg_text = " ".join([w for w in word_list if len(w) > 1]) # 过滤单字
                
                if seg_text.strip():
                    tfidf = TfidfVectorizer(max_features=10, stop_words=None)
                    tfidf.fit_transform([seg_text])
                    doc_keywords = tfidf.get_feature_names_out().tolist()
            except Exception as e:
                logging.warning(f"⚠️ 提取 {doc_name} 关键词失败: {e}，使用文件名作为关键词")
                doc_keywords = self._fallback_keywords(doc_name)
        else:
            doc_keywords = self._fallback_keywords(doc_name)

        # 构造元数据对象
        doc_meta = {
            "name": doc_name,
            "keywords": doc_keywords,
            "summary": doc_summary,
            "chunk_count": len(chunks)
        }
        
        # 更新全局索引
        self.doc_meta_info[doc_name] = doc_meta
        self.global_doc_keywords.extend(doc_keywords)
        # 去重并保持列表大小适中
        self.global_doc_keywords = list(set(self.global_doc_keywords))[-500:]

        return doc_meta

    def _fallback_keywords(self, doc_name: str) -> List[str]:
        """兜底关键词提取策略"""
        base_name = os.path.splitext(doc_name)[0]
        # 用下划线或空格分割文件名
        import re
        return [w for w in re.split(r"[_ -]", base_name) if w.strip()]

    def add_file(self, file_path: str):
            """
            加载文件 -> 智能解析 -> 注入上下文元数据 -> 存入向量库
            """
            try:
                if not isinstance(file_path, str): raise TypeError(f"file_path must be str")
                file_path = os.path.abspath(file_path)
                if not os.path.exists(file_path): raise FileNotFoundError(f"文件不存在: {file_path}")
                
                doc_name = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                # 检查去重逻辑... (保持不变)
                if hasattr(self.vector_store, "get"):
                    existing = self.vector_store.get(where={"file_hash": file_hash}, limit=1)
                    if existing and existing.get("ids"):
                        logging.info(f"⚠️ 文件已存在，跳过添加: {doc_name}")
                        return

                logging.info(f"📄 Processing file: {doc_name}")
                chunks = self.ingestion.process_documents(file_path)
                
                if not chunks: return

                # ========================================================
                # [核心优化 1]：注入上下文缓冲 (Context Buffering)
                # ========================================================
                # 我们在 metadata 中预存前后文，这样检索到切片时，
                # 即使物理切割了，也能通过 metadata 找回断掉的句子。
                # ========================================================
                total_chunks = len(chunks)
                CONTEXT_BUFFER_SIZE = 250  # 预存前后 250 个字符

                for i, chunk in enumerate(chunks):
                    # 基础元数据
                    chunk.metadata["file_hash"] = file_hash
                    chunk.metadata["file_name"] = doc_name
                    chunk.metadata["chunk_index"] = i  # 记录顺序 ID，这很重要
                    chunk.metadata["total_chunks"] = total_chunks
                    
                    # 注入前文 (Look-behind)
                    if i > 0:
                        prev_text = chunks[i-1].page_content
                        # 取上一段的最后 N 个字符
                        chunk.metadata["prev_buffer"] = prev_text[-CONTEXT_BUFFER_SIZE:]
                    else:
                        chunk.metadata["prev_buffer"] = ""

                    # 注入后文 (Look-ahead) -> 解决“问题在页末，答案在下页”的关键
                    if i < total_chunks - 1:
                        next_text = chunks[i+1].page_content
                        # 取下一段的开始 N 个字符
                        chunk.metadata["next_buffer"] = next_text[:CONTEXT_BUFFER_SIZE]
                    else:
                        chunk.metadata["next_buffer"] = ""

                doc_meta = self._generate_meta_from_chunks(chunks, doc_name)
                self.vector_store.add_documents(chunks)
                logging.info(f"✅ 已添加 {len(chunks)} 个切片 (带上下文缓冲)")
                    
            except Exception as e:
                logging.error(f"❌ Error adding file {file_path}: {str(e)}")
                raise e
    def search(self, query: str, expand_context: bool = True) -> str:
        """
        检索并融合上下文
        Args:
            expand_context: 是否启用利用 metadata 进行上下文补全
        """
        try:
            # 1. 基础检索
            docs = self.vector_store.similarity_search(query, k=self.config.search_top_k)
            if not docs: return ""

            # ========================================================
            # [核心优化 2]：智能结果融合 (Smart Result Merging)
            # ========================================================
            # 如果检索出了 [Chunk 5, Chunk 6, Chunk 10]，
            # 应该把 5 和 6 合并展示，而不是分开。
            # ========================================================
            
            # 按 (file_hash, chunk_index) 分组排序
            # 结构: { "hash_xxx": [doc_obj_1, doc_obj_2] }
            grouped_docs = {}
            for doc in docs:
                f_hash = doc.metadata.get("file_hash", "unknown")
                if f_hash not in grouped_docs:
                    grouped_docs[f_hash] = []
                grouped_docs[f_hash].append(doc)

            final_results = []
            
            for f_hash, group in grouped_docs.items():
                # 按 chunk_index 排序，确保合并顺序正确
                group.sort(key=lambda x: x.metadata.get("chunk_index", 0))
                
                merged_texts = []
                current_block = []
                last_index = -999

                for doc in group:
                    current_index = doc.metadata.get("chunk_index", 0)
                    content = doc.page_content.strip()
                    
                    # 检查是否连续 (允许 index 差 1)
                    if current_index == last_index + 1:
                        # 是连续的 chunk，直接合并到当前块
                        current_block.append(content)
                    else:
                        # 不连续，先结算上一个块
                        if current_block:
                            merged_texts.append(current_block)
                        # 开启新块
                        current_block = [content]
                        
                        # [补全逻辑]：如果是新块的开头，检查是否需要利用 metadata 补全“前文”
                        # 只有当这是整个检索列表的第一个，且不在开头时才补，避免冗余
                        if expand_context and doc.metadata.get("prev_buffer"):
                            # 只有当句子看起来被截断时才补全（简单判断：不大写开头，或之前的标点不是句号）
                            # 这里简单处理：直接补上，让 LLM 自己判断
                            pass 

                    # [补全逻辑]：利用 Metadata 补全“后文” (Look-ahead)
                    # 只有当这个 doc 是孤立的，或者它是连续块的最后一个时，才尝试补全
                    # 注意：如果下一个 chunk 已经在 group 里了，就不要补全 metadata，否则会重复
                    is_last_in_group = (doc == group[-1])
                    next_is_missing = True
                    if not is_last_in_group:
                         next_doc_index = group[group.index(doc) + 1].metadata.get("chunk_index", 0)
                         if next_doc_index == current_index + 1:
                             next_is_missing = False

                    if expand_context and next_is_missing and doc.metadata.get("next_buffer"):
                        # 添加一个特殊的标记，告诉 LLM 这是自动补全的上下文
                        buffer_text = doc.metadata["next_buffer"]
                        # 为了不污染 current_block 的纯文本，我们在最终输出时处理，
                        # 或者在这里简单拼接
                        current_block.append(f" [>>接下文: {buffer_text}...] ")

                    last_index = current_index

                # 结算最后一个块
                if current_block:
                    merged_texts.append(current_block)

                # 格式化输出
                source_name = group[0].metadata.get("file_name", "Unknown")
                for i, block in enumerate(merged_texts):
                    # block 是一个 list，里面可能是 [chunk_N_content, chunk_N+1_content]
                    # 或者 [chunk_N_content, buffer_text]
                    full_text = "".join(block)
                    # 清理可能产生的重复标记
                    full_text = full_text.replace("...]  [>>接下文:", "") 
                    
                    result_item = (
                        f"--- [引用] 来源: {source_name} (片段 {i+1}) ---\n"
                        f"{full_text}\n"
                    )
                    final_results.append(result_item)
            
            return "\n".join(final_results)
            
        except Exception as e:
            logging.error(f"❌ Search failed: {str(e)}")
            # 降级策略：如果高级融合失败，回退到简单拼接
            return "\n".join([d.page_content for d in docs])

    def clear_knowledge_base(self):
        """(危险操作) 清空知识库"""
        try:
            if self.config.vector_store.provider == "chroma":
                path = self.config.vector_store.persist_path
                if os.path.exists(path):
                    shutil.rmtree(path)
                    os.makedirs(path, exist_ok=True)
                    logging.info(f"✅ Chroma 知识库已重置: {path}")

            elif self.config.vector_store.provider == "qdrant":
                # 获取 Qdrant client
                from qdrant_client import QdrantClient
                from qdrant_client.models import Filter, FilterSelector

                url = self.config.vector_store.get_url() if hasattr(self.config.vector_store, 'get_url') else (
                    self.config.vector_store.url or "http://localhost:6333"
                )

                client = QdrantClient(url=url)
                collection_name = self.config.vector_store.collection_name

                # 删除集合中的所有数据 - 使用空的 Filter 来匹配所有点
                client.delete(
                    collection_name=collection_name,
                    points_selector=FilterSelector(
                        filter=Filter(must=[])  # 空条件匹配所有点
                    )
                )
                logging.info(f"✅ Qdrant 集合 '{collection_name}' 中的所有数据已清空")

            else:
                logging.warning("当前配置不支持自动清空")

            # 清空内存中的元数据
            self.doc_meta_info = {}
            self.global_doc_keywords = []

        except Exception as e:
            logging.error(f"❌ 清空知识库失败: {str(e)}")

    def get_global_keywords(self) -> List[str]:
        return self.global_doc_keywords

    def get_all_doc_meta(self) -> Dict[str, dict]:
        return self.doc_meta_info

__all__ = ["RAGService"]


# ====================== 测试代码 ======================
if __name__ == "__main__":
    # 导入配置类（顶部已处理路径问题）
    try:
        from .config import EmbeddingConfig, VectorStoreConfig
    except ImportError:
        from aigility.rag.config import EmbeddingConfig, VectorStoreConfig
    
    # 配置日志输出到控制台
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )
    
    print("=" * 60)
    print("🧪 RAGService 功能测试")
    print("=" * 60)
    
    # ----------------------
    # 测试配置（使用本地 HuggingFace 模型 + Chroma）
    # ----------------------
    try:
        from .config import IngestionConfig
    except ImportError:
        from aigility.rag.config import IngestionConfig
    
    config = RAGConfig(
        embedding=EmbeddingConfig(
            provider="zhipuai",
            model_name="embedding-3",
            api_key=os.getenv("ZHIPUAI_API_KEY", "")
        ),
        vector_store=VectorStoreConfig(
            provider="qdrant",
            collection_name="adp_knowledge_base",
            url="http://localhost:6333" 
        ),
        ingestion=IngestionConfig(
            chunk_size=500,
            chunk_overlap=50,  # 增大 overlap，确保跨页内容有重叠
        ),
        search_top_k=5
    )
    
    print(f"\n📋 配置信息:")
    print(f"   - Embedding: {config.embedding.provider} / {config.embedding.model_name}")
    print(f"   - VectorStore: {config.vector_store.provider}")
    print(f"   - 持久化路径: {config.vector_store.get_persist_path()}")
    print(f"   - Chunk Size: {config.ingestion.chunk_size}, Overlap: {config.ingestion.chunk_overlap}")
    
    # ----------------------
    # 初始化服务
    # ----------------------
    print("\n📦 初始化 RAGService...")
    try:
        service = RAGService(config=config)
        print("   ✅ 初始化成功！")
    except Exception as e:
        print(f"   ❌ 初始化失败: {e}")
        sys.exit(1)
    
    # ----------------------
    # 添加测试文件
    # ----------------------
    # 查找测试文件
    test_files = ["test.pdf", "test.txt", "aigility/rag/test.pdf", "aigility/rag/test.txt",
                  "../test.pdf", "../../test.pdf"]
    test_file = None
    for f in test_files:
        if os.path.exists(f):
            test_file = f
            break
    
    if test_file:
        print(f"\n📄 添加测试文件: {test_file}")
        try:
            service.add_file(test_file)
            print("   ✅ 文件处理完成！")
        except Exception as e:
            print(f"   ❌ 文件处理失败: {e}")
    else:
        print("\n⚠️ 未找到测试文件，跳过文件添加步骤")
        print("   请在当前目录放置 test.pdf 或 test.txt 文件")
    
    # ----------------------
    # 查看文档元信息
    # ----------------------
    print("\n📊 文档元信息:")
    all_meta = service.get_all_doc_meta()
    if all_meta:
        for doc_name, meta in all_meta.items():
            print(f"   📄 {doc_name}")
            print(f"      - 关键词: {meta.get('keywords', [])}")
            print(f"      - 切片数: {meta.get('chunk_count', 0)}")
            print(f"      - 摘要: {meta.get('summary', '')[:100]}...")
    else:
        print("   (无文档)")
    
    # ----------------------
    # 测试检索
    # ----------------------
    print("\n🔍 测试检索功能:")
    test_queries = [

        "应届生毕业后档案有哪些去处？"
    ]
    
    for query in test_queries:
        print(f"\n   Q: {query}")
        result = service.search(query)
        if result:
            # 只显示前 500 个字符
            preview = result[:500] + "..." if len(result) > 500 else result
            print(f"   A: {result}")
        else:
            print("   A: (无匹配结果)")
    
    # ----------------------
    # 全局关键词
    # ----------------------
    print("\n🏷️ 全局关键词:")
    keywords = service.get_global_keywords()
    print(f"   {keywords[:20]}{'...' if len(keywords) > 20 else ''}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)