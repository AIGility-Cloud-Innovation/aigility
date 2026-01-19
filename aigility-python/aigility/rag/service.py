# rag_service.py
# [服务层] 对外暴露的统一入口 (RAGService)

import os
import sys
import shutil
import hashlib
import logging
from typing import Optional, Dict, List

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
        加载文件 -> 智能解析 -> 存入向量库
        """
        try:
            if not isinstance(file_path, str):
                raise TypeError(f"file_path must be str, got {type(file_path)}")
            
            file_path = os.path.abspath(file_path)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            doc_name = os.path.basename(file_path)
            
            # 1. 计算文件 Hash (用于去重)
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            # 2. 检查是否已存在
            existing = self.vector_store.get(where={"file_hash": file_hash}, limit=1)
            if existing and existing.get("ids"):
                logging.info(f"⚠️ 文件已存在，跳过添加: {doc_name}")
                return

            logging.info(f"📄 Processing file: {doc_name}")

            # 3. 调用 IngestionManager 进行一站式处理
            # 这里调用的是优化后的 process_documents，它会自动处理 PDF 表格转 Markdown、Excel 转 KV 对
            chunks = self.ingestion.process_documents(file_path)
            
            if not chunks:
                logging.warning(f"❌ {doc_name} 解析后无有效内容")
                return

            # 4. 补充元数据 (File Hash)
            for chunk in chunks:
                chunk.metadata["file_hash"] = file_hash

            # 5. 生成文档级元信息 (基于解析后的高质量文本)
            doc_meta = self._generate_meta_from_chunks(chunks, doc_name)
            logging.info(f"✅ 生成元信息: 关键词={doc_meta['keywords']}")

            # 6. 存入向量库
            self.vector_store.add_documents(chunks)
            logging.info(f"✅ 已添加 {len(chunks)} 个切片到知识库")
                
        except Exception as e:
            logging.error(f"❌ Error adding file {file_path}: {str(e)}")
            raise e

    def search(self, query: str) -> str:
        """
        检索相关文档，返回格式化字符串供 LLM 使用
        """
        try:
            # 语义检索
            docs = self.vector_store.similarity_search(query, k=self.config.search_top_k)
            
            if not docs:
                return ""

            results = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("file_name", "Unknown")
                # 移除多余换行，保持紧凑
                content = doc.page_content.strip()
                
                # 构造引用格式，包含来源
                result_item = (
                    f"--- [引用 {i+1}] 来源: {source} ---\n"
                    f"{content}\n"
                )
                results.append(result_item)
            
            return "\n".join(results)
            
        except Exception as e:
            logging.error(f"❌ Search failed: {str(e)}")
            return ""

    def clear_knowledge_base(self):
        """(危险操作) 清空知识库"""
        try:
            if self.config.vector_store.provider == "chroma":
                path = self.config.vector_store.persist_path
                if os.path.exists(path):
                    shutil.rmtree(path)
                    os.makedirs(path, exist_ok=True)
                    logging.info(f"✅ Chroma 知识库已重置: {path}")
            # ... 其他 vector store 的清理逻辑保持不变 ...
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
            provider="huggingface",
            model_name="BAAI/bge-small-zh-v1.5",
            kwargs={"model_kwargs": {"device": "cpu"}}
        ),
        vector_store=VectorStoreConfig(
            provider="chroma",
            collection_name="test_collection",
            persist_path="./test_chroma_db"
        ),
        ingestion=IngestionConfig(
            chunk_size=500,
            chunk_overlap=100,  # 增大 overlap，确保跨页内容有重叠
        ),
        search_top_k=3
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
    test_files = ["test.pdf", "test.txt", "../test.pdf", "../../test.pdf"]
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
        "五险一金是什么",
        "无领导小组面试考察什么？",
        ".面试形式和种类有哪些？"
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