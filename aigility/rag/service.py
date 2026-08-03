# rag_service.py
# [服务层] 对外暴露的统一入口 (RAGService)

import os
import sys
import shutil
import hashlib
import logging
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, List
from collections import defaultdict

from .usage_tracking import UsageStats, TokenUsage, SearchResult, AddFileResult
from .embeddings.wrapper import EmbeddingWrapper

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
    from .rerank.factory import RerankFactory
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
    from aigility.rag.rerank.factory import RerankFactory

# NLP 依赖用于提取元数据 (关键词/摘要)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import jieba
    HAS_NLP_DEPS = True
except ImportError:
    HAS_NLP_DEPS = False

# BM25 依赖（可选）
try:
    from rank_bm25 import BM25Okapi
    HAS_RANK_BM25 = True
except ImportError:
    HAS_RANK_BM25 = False


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
        raw_embedding = EmbeddingFactory.get_embedding_model(self.config.embedding)
        self.embedding_model = raw_embedding
        self._embedding_wrapper = EmbeddingWrapper(raw_embedding)

        # 2. 初始化 Vector Store (注入 wrapper 以追踪 usage)
        self.vector_store = VectorStoreFactory.get_vector_store(
            self.config.vector_store,
            self._embedding_wrapper
        )

        # 2.1 确保 Payload Index 已建立（仅 Qdrant）
        if self.config.vector_store.provider == "qdrant":
            try:
                from .vector_stores.qdrant import QdrantAdapter
                QdrantAdapter.ensure_payload_indexes(
                    self.vector_store.client,
                    self.config.vector_store
                )
            except Exception as e:
                logging.warning(f"⚠️ Payload Index 初始化失败: {e}")
        
        # 3. 初始化数据处理模块 (核心解析逻辑在此)
        self.ingestion = IngestionManager(self.config.ingestion)

        # 4. 文档元信息存储 (内存缓存，生产环境建议持久化到 SQLite/MySQL)
        self.doc_meta_info: Dict[str, dict] = {}
        self.global_doc_keywords: List[str] = []

        # 5. BM25 混合检索（延迟初始化）
        self._bm25_corpus = []  # BM25 语料库
        self._bm25_doc_mapping = {}  # 文档映射
        self._bm25_index = None  # BM25 索引
        self._bm25_built = False  # 索引是否已构建

        # 6. Rerank 重排序（可选）
        self._reranker = None
        if self.config.rerank.enabled:
            try:
                self._reranker = RerankFactory.get_reranker(self.config.rerank)
                logging.info(f"✅ Rerank 已启用: {self.config.rerank.provider}/{self.config.rerank.model_name}")
            except Exception as e:
                logging.warning(f"⚠️ Rerank 初始化失败，将跳过 rerank: {e}")

        # 7. Usage 追踪
        self._total_usage = UsageStats()
        self._usage_callbacks: List[Callable[[UsageStats], None]] = []

    @property
    def usage(self) -> UsageStats:
        """累计 token 用量"""
        return self._total_usage

    def on_usage(self, callback: Callable[[UsageStats], None]):
        """注册 usage 回调，每次 API 调用后触发"""
        self._usage_callbacks.append(callback)

    def reset_usage(self):
        """重置累计用量"""
        self._total_usage = UsageStats()

    def _notify_usage(self, usage: UsageStats):
        for cb in self._usage_callbacks:
            try:
                cb(usage)
            except Exception as e:
                logging.warning(f"⚠️ Usage callback error: {e}")

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

    def _boost_keyword_matches(self, query: str, docs: List, top_k: int) -> List:
        """
        关键词增强：提升包含精确关键词的文档的排名

        Args:
            query: 查询文本
            docs: 候选文档列表
            top_k: 返回数量

        Returns:
            重新排序后的文档列表
        """
        import re

        # 提取查询中的关键词和短语
        keywords = set()
        phrases = []

        # 分词并过滤停用词
        for word in query.split():
            if len(word) > 1 and word not in {'的', '了', '是', '在', '和', '与', '或', '|||'}:
                keywords.add(word)

        # 提取2-3个词的短语组合
        words_list = [w for w in query.split() if len(w) > 1 and w not in {'的', '了', '是', '在', '和', '与', '或', '|||'}]
        if len(words_list) >= 2:
            # 2词短语
            for i in range(len(words_list) - 1):
                phrases.append(f"{words_list[i]}{words_list[i+1]}")  # 无空格
                phrases.append(f"{words_list[i]} {words_list[i+1]}")  # 有空格
        if len(words_list) >= 3:
            # 3词短语
            for i in range(len(words_list) - 2):
                phrases.append(f"{words_list[i]}{words_list[i+1]}{words_list[i+2]}")
                phrases.append(f"{words_list[i]} {words_list[i+1]} {words_list[i+2]}")

        if not keywords and not phrases:
            return docs[:top_k]

        # 计算每个文档的关键词匹配分数
        scored_docs = []
        for doc in docs:
            content = doc.page_content.lower()
            score = 0

            # 1. 完整短语匹配（最高优先级）
            for phrase in phrases:
                phrase_lower = phrase.lower()
                if phrase_lower in content:
                    score += 200  # 短语匹配给高分

            # 2. 关键词匹配
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in content:
                    # 关键词出现次数
                    count = content.count(kw_lower)
                    score += count * 50  # 每次出现加50分

                    # 如果是完整词匹配（前后有边界），额外加分
                    if re.search(r'\b' + re.escape(kw_lower) + r'\b', content):
                        score += 30

            # 保存分数
            if score > 0:
                scored_docs.append((doc, score))
            else:
                scored_docs.append((doc, 0))

        # 按分数排序（分数高的在前）
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 返回前 top_k 个文档
        return [doc for doc, score in scored_docs[:top_k]]

    def add_file(self, file_path: str, auto_build_bm25: bool = True) -> AddFileResult:
            """
            加载文件 -> 智能解析 -> 注入上下文元数据 -> 存入向量库

            Args:
                file_path: 文件路径
                auto_build_bm25: 是否自动构建BM25索引（默认True）
                                 批量添加文件时建议设为False，最后统一调用build_bm25_index()

            Returns:
                AddFileResult 对象，包含：
                - file_hash: 基于文件内容的MD5哈希（用于删除操作）
                - file_name: 文件名（用于删除操作）
                - usage: 本次操作的 token 用量（embedding tokens）

            注意：
                - 返回的 file_hash 可用于后续的 delete_document 和 restore_document 操作
                - 相同内容的文件会有相同的 file_hash
                - 使用 file_hash 删除时会删除所有相同内容的文件
                - 批量添加文件时建议设置 auto_build_bm25=False，最后手动调用 build_bm25_index(force_rebuild=True)
            """
            try:
                if not isinstance(file_path, str): raise TypeError(f"file_path must be str")
                file_path = os.path.abspath(file_path)
                if not os.path.exists(file_path): raise FileNotFoundError(f"文件不存在: {file_path}")

                doc_name = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()

                # 检查是否存在相同 file_hash 的文件（包括已删除的）
                # 如果存在，恢复并更新元数据；否则添加新文件
                existing_with_same_hash = None

                # 使用Qdrant client直接查询（更可靠）
                if self.config.vector_store.provider == "qdrant":
                    try:
                        from qdrant_client.models import Filter, FieldCondition, MatchValue

                        client = self.vector_store.client
                        collection_name = self.vector_store.collection_name

                        points, _ = client.scroll(
                            collection_name=collection_name,
                            scroll_filter=Filter(
                                must=[
                                    FieldCondition(
                                        key="metadata.file_hash",
                                        match=MatchValue(value=file_hash)
                                    )
                                ]
                            ),
                            limit=1,
                            with_payload=True
                        )

                        if points:
                            # 转换为get方法返回的格式
                            existing_with_same_hash = {
                                "ids": [p.id for p in points],
                                "metadatas": [p.payload.get("metadata", {}) for p in points]
                            }
                            logging.info(f"🔍 检测到相同file_hash的文件: {file_hash}")

                    except Exception as e:
                        logging.warning(f"⚠️ 查询file_hash失败: {e}，使用原有方法")

                # 如果不是Qdrant或查询失败，使用原有方法
                if not existing_with_same_hash and hasattr(self.vector_store, "get"):
                    vector_store_type = self.config.vector_store.provider

                    if vector_store_type == "chroma":
                        # Chroma: 查找所有相同 file_hash 的文件
                        existing_with_same_hash = self.vector_store.get(
                            where={"file_hash": file_hash},
                            limit=1
                        )
                    else:
                        # 其他向量库
                        existing_with_same_hash = self.vector_store.get(
                            where={"file_hash": file_hash},
                            limit=1
                        )

                # 如果找到相同 file_hash 的文件（无论是否已删除）
                if existing_with_same_hash and existing_with_same_hash.get("ids"):
                    # 检查文件是否已删除
                    is_deleted = False
                    if existing_with_same_hash.get("metadatas"):
                        first_metadata = existing_with_same_hash["metadatas"][0]
                        # 对于 Qdrant，元数据可能嵌套在 payload 中
                        if isinstance(first_metadata, dict):
                            is_deleted = first_metadata.get("is_deleted", False)

                    if is_deleted:
                        # 文件已删除：恢复文件并更新文件名
                        logging.info(f"♻️ 检测到相同内容的已删除文件，恢复中: {doc_name} (hash: {file_hash[:16]}...)")
                        success = self.restore_document(file_hash=file_hash)

                        if success:
                            # 更新文件名为新上传的文件名
                            logging.info(f"📝 更新文件名: {doc_name}")
                            try:
                                self._update_chunks_metadata(
                                    file_hash=file_hash,
                                    metadata_update={"file_name": doc_name}
                                )
                            except Exception as e:
                                logging.warning(f"⚠️ 更新文件名失败: {e}")

                            logging.info(f"✅ 文件恢复成功，跳过重复添加")
                            return AddFileResult(
                                file_hash=file_hash,
                                file_name=doc_name,
                            )
                        else:
                            logging.warning(f"⚠️ 恢复文件失败，将作为新文件添加: {doc_name}")
                    else:
                        # 文件未删除：仅更新文件名（如果不同）
                        logging.info(f"✅ 文件已存在且未被删除: {doc_name} (hash: {file_hash[:16]}...)")
                        logging.info(f"ℹ️  跳过重复添加， chunks已存在于数据库中")
                        return AddFileResult(
                            file_hash=file_hash,
                            file_name=doc_name,
                        )

                logging.info(f"📄 Processing file: {doc_name}")
                chunks = self.ingestion.process_documents(file_path)

                if not chunks:
                    return AddFileResult(
                        file_hash=file_hash,
                        file_name=doc_name,
                    )

                # ========================================================
                # 注入元数据 + 上下文扩展
                # ========================================================
                total_chunks = len(chunks)
                created_at = datetime.now(timezone.utc).isoformat()

                if self.config.ingestion.enable_small2big:
                    # Small2Big: parent_text 已由 splitter 注入 metadata
                    # 这里只需要注入 file_hash 相关的元数据和 parent_chunk_id
                    for i, chunk in enumerate(chunks):
                        chunk.metadata["file_hash"] = file_hash
                        chunk.metadata["file_name"] = doc_name
                        chunk.metadata["source_file"] = doc_name
                        chunk.metadata["chunk_id"] = f"{file_hash}_c{i:04d}"
                        chunk.metadata["chunk_index"] = i
                        chunk.metadata["total_chunks"] = total_chunks
                        chunk.metadata["is_deleted"] = False
                        chunk.metadata["created_at"] = created_at
                        # 注入真实的 parent_chunk_id（splitter 不知道 file_hash）
                        parent_idx = chunk.metadata.get("parent_index", 0)
                        chunk.metadata["parent_chunk_id"] = f"{file_hash}_p{parent_idx:04d}"
                else:
                    # Legacy: 注入 prev/next buffer
                    CONTEXT_BUFFER_SIZE = 250
                    for i, chunk in enumerate(chunks):
                        chunk.metadata["file_hash"] = file_hash
                        chunk.metadata["file_name"] = doc_name
                        chunk.metadata["source_file"] = doc_name
                        chunk.metadata["chunk_id"] = f"{file_hash}_c{i:04d}"
                        chunk.metadata["chunk_index"] = i
                        chunk.metadata["total_chunks"] = total_chunks
                        chunk.metadata["is_deleted"] = False
                        chunk.metadata["created_at"] = created_at

                        if i > 0:
                            prev_text = chunks[i-1].page_content
                            chunk.metadata["prev_buffer"] = prev_text[-CONTEXT_BUFFER_SIZE:]
                        else:
                            chunk.metadata["prev_buffer"] = ""

                        if i < total_chunks - 1:
                            next_text = chunks[i+1].page_content
                            chunk.metadata["next_buffer"] = next_text[:CONTEXT_BUFFER_SIZE]
                        else:
                            chunk.metadata["next_buffer"] = ""

                doc_meta = self._generate_meta_from_chunks(chunks, doc_name)

                # 预计算 embeddings 并追踪 usage，然后通过 context manager 防止向量库重复 embedding
                texts = [chunk.page_content for chunk in chunks]
                precomputed_embeddings = self._embedding_wrapper.embed_documents(texts)
                add_usage = UsageStats(
                    embedding=self._embedding_wrapper.last_usage or TokenUsage()
                )
                self._embedding_wrapper.reset_usage()

                with self._embedding_wrapper.use_precomputed(texts, precomputed_embeddings):
                    self.vector_store.add_documents(chunks)

                if self.config.ingestion.enable_small2big:
                    logging.info(f"✅ 已添加 {len(chunks)} 个切片 (Small2Big: parent→child)")
                else:
                    logging.info(f"✅ 已添加 {len(chunks)} 个切片 (带上下文缓冲)")

                # 自动构建BM25索引
                if auto_build_bm25:
                    try:
                        self.build_bm25_index()
                        logging.info(f"🔄 BM25索引已自动更新")
                    except Exception as e:
                        logging.warning(f"⚠️ BM25索引构建失败: {e}")

                self._total_usage += add_usage
                self._notify_usage(add_usage)

                return AddFileResult(
                    file_hash=file_hash,
                    file_name=doc_name,
                    usage=add_usage,
                )

            except Exception as e:
                logging.error(f"❌ Error adding file {file_path}: {str(e)}")
                raise e
    def search(self, query: str, expand_context: bool = True, enable_keyword_boost: bool = True) -> SearchResult:
        """
        检索并融合上下文（使用BM25混合检索）

        这是默认的检索方法，内部使用BM25混合检索以获得最佳的检索效果。

        Args:
            query: 查询文本
            expand_context: 是否启用利用 metadata 进行上下文补全（默认True）
            enable_keyword_boost: 是否启用关键词增强（默认True）
                                 - True: 增加BM25权重（0.6），适合精确查询
                                 - False: 平衡权重（0.5），适合语义查询

        Returns:
            SearchResult 对象，包含 content (str), documents, usage, metadata

        示例:
            >>> result = service.search("目标市场")
            >>> print(str(result))  # 格式化字符串（向后兼容）
            >>> print(result.usage.embedding.total_tokens)  # embedding token 消耗
        """
        try:
            # 根据enable_keyword_boost设置BM25权重
            if enable_keyword_boost:
                # 启用关键词增强：增加BM25权重，更适合精确查询
                bm25_weight = 0.6
                semantic_weight = 0.4
            else:
                # 不启用关键词增强：平衡权重，更适合语义查询
                bm25_weight = 0.5
                semantic_weight = 0.5

            # 使用BM25混合检索
            result = self.search_bm25_hybrid(
                query=query,
                semantic_weight=semantic_weight,
                bm25_weight=bm25_weight,
                expand_context=expand_context
            )
            self._total_usage += result.usage
            self._notify_usage(result.usage)
            return result

        except Exception as e:
            logging.error(f"❌ Search failed: {str(e)}")
            # 降级策略：使用纯语义检索
            docs = self._search_with_filter(query, k=self.config.search_top_k)
            content = self._format_search_results(docs, expand_context)
            fallback_usage = UsageStats(
                embedding=self._embedding_wrapper.last_usage or TokenUsage()
            )
            self._embedding_wrapper.reset_usage()
            result = SearchResult(content=content, documents=docs, usage=fallback_usage)
            self._total_usage += fallback_usage
            self._notify_usage(fallback_usage)
            return result

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

            # 清空BM25索引
            self._bm25_corpus = []
            self._bm25_doc_mapping = {}
            self._bm25_index = None
            self._bm25_built = False
            logging.info("✅ BM25索引已清空")

        except Exception as e:
            logging.error(f"❌ 清空知识库失败: {str(e)}")

    def _search_with_filter(self, query: str, k: int = 5) -> List:
        """
        带过滤条件的检索，只返回未删除的chunk

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            检索结果列表
        """
        try:
            # 根据不同的vector store实现使用不同的过滤方式
            vector_store_type = self.config.vector_store.provider

            if vector_store_type == "chroma":
                # Chroma使用where参数过滤
                docs = self.vector_store.similarity_search(
                    query,
                    k=k,
                    filter={"is_deleted": {"$ne": True}}  # is_deleted != True
                )
            elif vector_store_type == "qdrant":
                # Qdrant: 使用字典格式的filter
                # LangChain 的 Qdrant adapter 接受字典格式的 filter
                docs = self.vector_store.similarity_search(
                    query,
                    k=k,
                    filter={"is_deleted": False}
                )
            else:
                # 其他向量库，先检索然后手动过滤
                all_docs = self.vector_store.similarity_search(query, k=k * 3)  # 多取一些以确保有足够结果
                docs = [doc for doc in all_docs if doc.metadata.get("is_deleted") != True][:k]

            return docs
        except Exception as e:
            logging.warning(f"⚠️ 过滤检索失败，降级为普通检索: {str(e)}")
            # 降级策略：使用普通检索
            docs = self.vector_store.similarity_search(query, k=k)
            return [doc for doc in docs if doc.metadata.get("is_deleted") != True]

    def delete_document(
        self,
        file_name: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> bool:
        """
        软删除文档（标记为已删除，不实际从向量库中删除）

        Args:
            file_name: 文件名（如果有多个同名文件会全部删除）
            file_hash: 文件哈希值（基于文件内容，推荐使用）

        Returns:
            是否删除成功

        注意：
            - 推荐使用 file_hash，因为它基于内容且唯一
            - 使用 file_name 会删除所有同名文件
            - file_hash 是基于文件内容的MD5，相同内容的文件会有相同的hash
        """
        try:
            # 至少需要一个标识符
            if not file_name and not file_hash:
                raise ValueError("必须提供 file_name 或 file_hash 参数")

            # 构建过滤条件
            filter_dict = {}
            if file_hash:
                filter_dict["file_hash"] = file_hash
            if file_name:
                filter_dict["file_name"] = file_name

            # 更新所有匹配的chunk的metadata
            success = self._update_chunks_metadata(
                filter_dict=filter_dict,
                updates={"is_deleted": True}
            )

            if success:
                identifier = file_hash or file_name
                logging.info(f"✅ 文档已标记为删除: {identifier}")

            return success

        except Exception as e:
            logging.error(f"❌ 删除文档失败: {str(e)}")
            return False

    def restore_document(
        self,
        file_name: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> bool:
        """
        恢复已删除的文档

        Args:
            file_name: 文件名（如果有多个同名文件会全部恢复）
            file_hash: 文件哈希值（基于文件内容，推荐使用）

        Returns:
            是否恢复成功

        注意：
            - 推荐使用 file_hash，因为它基于内容且唯一
            - 使用 file_name 会恢复所有同名文件
        """
        try:
            # 至少需要一个标识符
            if not file_name and not file_hash:
                raise ValueError("必须提供 file_name 或 file_hash 参数")

            # 构建过滤条件
            filter_dict = {}
            if file_hash:
                filter_dict["file_hash"] = file_hash
            if file_name:
                filter_dict["file_name"] = file_name

            # 更新所有匹配的chunk的metadata
            success = self._update_chunks_metadata(
                filter_dict=filter_dict,
                updates={"is_deleted": False}
            )

            if success:
                identifier = file_hash or file_name
                logging.info(f"✅ 文档已恢复: {identifier}")

            return success

        except Exception as e:
            logging.error(f"❌ 恢复文档失败: {str(e)}")
            return False

    def _update_chunks_metadata(self, filter_dict: Dict, updates: Dict) -> bool:
        """
        更新匹配条件的chunk的metadata

        Args:
            filter_dict: 过滤条件，例如 {"file_name": "test.pdf"}
            updates: 要更新的字段，例如 {"is_deleted": True}

        Returns:
            是否更新成功
        """
        try:
            vector_store_type = self.config.vector_store.provider

            if vector_store_type == "chroma":
                # Chroma: 使用update方法
                # 1. 先查询符合条件的文档
                results = self.vector_store.get(where=filter_dict, limit=None)
                if results and results.get("ids"):
                    # 2. 更新metadata
                    metadatas = results["metadatas"]
                    ids = results["ids"]

                    # 应用更新
                    updated_metadatas = []
                    for metadata in metadatas:
                        new_metadata = metadata.copy()
                        new_metadata.update(updates)
                        updated_metadatas.append(new_metadata)

                    # 3. 执行更新
                    self.vector_store.update(
                        ids=ids,
                        metadatas=updated_metadatas
                    )
                    logging.info(f"✅ Chroma: 更新了 {len(ids)} 个chunk的metadata")
                    return True
                else:
                    logging.warning(f"⚠️ Chroma: 未找到匹配的文档，filter={filter_dict}")

            elif vector_store_type == "qdrant":
                # Qdrant: 使用overwrite_payload方法
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                # 获取client
                client = self.vector_store.client
                collection_name = self.config.vector_store.collection_name

                # 构建过滤条件 - 注意：LangChain 将 metadata 存在 payload['metadata'] 中
                must_conditions = []
                for key, value in filter_dict.items():
                    must_conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",  # 使用 metadata. 前缀访问嵌套字段
                            match=MatchValue(value=value)
                        )
                    )

                logging.debug(f"🔍 Qdrant scroll查询，filter={must_conditions}")

                # 查询符合条件的points
                points, _ = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=Filter(must=must_conditions) if must_conditions else None,
                    limit=10000,
                    with_payload=True
                )

                logging.debug(f"🔍 Qdrant scroll找到 {len(points)} 个points")

                if points:
                    # 更新每个point的payload
                    for point in points:
                        # 获取现有payload并更新 metadata 字段
                        payload = dict(point.payload) if point.payload else {}
                        metadata = dict(payload.get("metadata", {}))

                        # 应用更新
                        metadata.update(updates)
                        payload["metadata"] = metadata

                        # 使用overwrite_payload更新
                        client.overwrite_payload(
                            collection_name=collection_name,
                            payload=payload,
                            points=[point.id]
                        )

                    logging.info(f"✅ Qdrant: 更新了 {len(points)} 个chunk的metadata")
                    return True
                else:
                    logging.warning(f"⚠️ Qdrant: 未找到匹配的文档，filter={filter_dict}")

            else:
                logging.warning(f"⚠️ 不支持向量库 {vector_store_type} 的metadata更新")

            return False

        except Exception as e:
            logging.error(f"❌ 更新chunk metadata失败: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return False

    def get_deleted_documents(self) -> List[str]:
        """
        获取所有已删除的文档列表

        Returns:
            已删除文档的file_name列表
        """
        try:
            deleted_docs = set()

            # 根据不同的向量库实现不同的查询方式
            vector_store_type = self.config.vector_store.provider

            if vector_store_type == "chroma":
                # Chroma: 使用where参数查询
                results = self.vector_store.get(
                    where={"is_deleted": True},
                    limit=None
                )
                if results and results.get("metadatas"):
                    for metadata in results["metadatas"]:
                        file_name = metadata.get("file_name")
                        if file_name:
                            deleted_docs.add(file_name)

            elif vector_store_type == "qdrant":
                # Qdrant: 使用filter查询
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                client = self.vector_store.client
                collection_name = self.config.vector_store.collection_name

                # 注意：LangChain 将 metadata 存在 payload['metadata'] 中
                points, _ = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="metadata.is_deleted",  # 使用 metadata. 前缀
                                match=MatchValue(value=True)
                            )
                        ]
                    ),
                    limit=10000,
                    with_payload=True
                )

                for point in points:
                    metadata = self._get_qdrant_metadata(point.payload)
                    file_name = metadata.get("file_name")
                    if file_name:
                        deleted_docs.add(file_name)

            return list(deleted_docs)

        except Exception as e:
            logging.error(f"❌ 获取已删除文档列表失败: {str(e)}")
            return []

    def get_global_keywords(self) -> List[str]:
        return self.global_doc_keywords

    def get_all_doc_meta(self) -> Dict[str, dict]:
        return self.doc_meta_info

    def _get_qdrant_metadata(self, payload: dict) -> dict:
        """
        从 Qdrant payload 中提取 metadata
        LangChain 将 metadata 存储在 payload['metadata'] 中
        """
        if not payload:
            return {}

        # LangChain 的 Qdrant adapter 将 metadata 存储在嵌套的 'metadata' 字段中
        return payload.get("metadata", {})

    def debug_list_all_documents(self) -> List[Dict]:
        """
        [调试方法] 列出向量库中的所有文档及其metadata

        Returns:
            文档信息列表，每个元素包含 file_name, file_hash, is_deleted 等信息
        """
        try:
            vector_store_type = self.config.vector_store.provider
            documents = []

            if vector_store_type == "chroma":
                # Chroma: 获取所有文档
                results = self.vector_store.get(limit=None)
                if results and results.get("metadatas"):
                    for metadata in results["metadatas"]:
                        documents.append({
                            "file_name": metadata.get("file_name"),
                            "file_hash": metadata.get("file_hash"),
                            "is_deleted": metadata.get("is_deleted"),
                            "chunk_index": metadata.get("chunk_index")
                        })

            elif vector_store_type == "qdrant":
                # Qdrant: 获取所有文档
                client = self.vector_store.client
                collection_name = self.config.vector_store.collection_name

                # 获取集合中的所有点
                points, _ = client.scroll(
                    collection_name=collection_name,
                    limit=10000,
                    with_payload=True
                )

                for point in points:
                    metadata = self._get_qdrant_metadata(point.payload)
                    documents.append({
                        "file_name": metadata.get("file_name"),
                        "file_hash": metadata.get("file_hash"),
                        "is_deleted": metadata.get("is_deleted"),
                        "chunk_index": metadata.get("chunk_index")
                    })

            return documents

        except Exception as e:
            logging.error(f"❌ 调试：列出所有文档失败: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return []

    # ========================================================
    # BM25 混合检索功能
    # ========================================================

    def build_bm25_index(self, force_rebuild: bool = False):
        """
        构建 BM25 索引

        Args:
            force_rebuild: 是否强制重建索引（默认False，只在未构建时构建）

        注意：
            - 首次使用BM25检索前必须调用此方法
            - 添加/删除文档后建议重新构建索引
            - 索引构建过程可能需要几秒钟（取决于文档数量）
        """
        if self._bm25_built and not force_rebuild:
            logging.info("✅ BM25索引已存在，跳过构建（使用 force_rebuild=True 强制重建）")
            return

        try:
            import math
            import hashlib
            from collections import defaultdict

            logging.info("📦 开始构建BM25索引...")

            # 从向量库获取所有文档
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            client = self.vector_store.client
            collection_name = self.vector_store.collection_name

            points, _ = client.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=True
            )

            if not points:
                logging.warning("⚠️ 没有文档可用于构建BM25索引")
                return

            # 构建语料库
            self._bm25_corpus = []
            self._bm25_doc_mapping = {}

            for point in points:
                payload = point.payload
                metadata = payload.get('metadata', {})

                # 过滤已删除的文档
                if metadata.get('is_deleted', False):
                    continue

                content = payload.get('page_content', '')
                tokens = self._tokenize_for_bm25(content)

                # 使用索引号作为ID（简单可靠）
                doc_idx = len(self._bm25_corpus)

                self._bm25_corpus.append(tokens)
                self._bm25_doc_mapping[doc_idx] = {
                    'content': content,
                    'metadata': metadata,
                    'point_id': point.id
                }

            # 构建 BM25 索引
            if HAS_RANK_BM25:
                self._bm25_index = BM25Okapi(self._bm25_corpus, k1=1.5, b=0.75, epsilon=0.25)
                logging.info(f"✅ BM25索引构建完成 (使用 rank_bm25 库)")
            else:
                # 使用自定义BM25实现
                self._bm25_index = self._CustomBM25(self._bm25_corpus, k1=1.5, b=0.75)
                logging.info(f"✅ BM25索引构建完成 (使用自定义实现)")

            logging.info(f"   索引文档数: {len(self._bm25_corpus)}")
            avg_len = sum(len(doc) for doc in self._bm25_corpus) / len(self._bm25_corpus) if self._bm25_corpus else 0
            logging.info(f"   平均文档长度: {avg_len:.2f} 词")

            self._bm25_built = True

        except Exception as e:
            logging.error(f"❌ 构建BM25索引失败: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def _tokenize_for_bm25(self, text: str) -> List[str]:
        """
        为BM25分词

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        # 使用jieba分词（如果可用）
        if HAS_NLP_DEPS:
            words = jieba.lcut(text)
            # 过滤停用词和单字
            stopwords = {'的', '了', '是', '在', '和', '与', '或', '|||', '、', '，', '。', '（', '）', '(', ')', '[', ']'}
            return [w for w in words if len(w) > 1 and w not in stopwords]
        else:
            # 简单的空格和符号分词
            import re
            words = re.findall(r'[\w]+', text)
            return [w for w in words if len(w) > 1]

    def _bm25_search(self, query: str, top_k: int = 5) -> List:
        """
        BM25 关键词检索

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            [(doc, score), ...] 检索结果列表
        """
        if not self._bm25_built:
            logging.warning("⚠️ BM25索引未构建，请先调用 build_bm25_index()")
            return []

        try:
            # 查询分词
            query_tokens = self._tokenize_for_bm25(query)

            if not query_tokens:
                return []

            # BM25检索
            scores = self._bm25_index.get_scores(query_tokens)

            # 排序并获取top_k
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

            # 转换为文档对象
            from langchain_core.documents import Document
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # 只返回有分数的文档
                    doc_info = self._bm25_doc_mapping.get(idx)

                    if doc_info:
                        doc = Document(
                            page_content=doc_info['content'],
                            metadata=doc_info['metadata']
                        )
                        results.append((doc, scores[idx]))

            return results

        except Exception as e:
            logging.error(f"❌ BM25检索失败: {e}")
            return []

    def search_bm25_hybrid(
        self,
        query: str,
        semantic_weight: float = 0.6,
        bm25_weight: float = 0.4,
        expand_context: bool = True
    ) -> SearchResult:
        """
        BM25混合检索：结合语义检索和关键词检索

        这是推荐的生产环境检索方法，结合了：
        - 语义检索：理解查询意图，找到语义相关的内容
        - BM25检索：精确关键词匹配，确保关键信息不遗漏

        Args:
            query: 查询文本
            semantic_weight: 语义检索权重（0-1，默认0.5）
            bm25_weight: BM25检索权重（0-1，默认0.5）
            expand_context: 是否扩展上下文（默认True）

        Returns:
            SearchResult 对象，包含 content, documents, usage, metadata

        使用示例：
            >>> service.build_bm25_index()
            >>> result = service.search_bm25_hybrid("目标市场")
            >>> print(str(result))
            >>> print(result.usage.embedding.total_tokens)
        """
        search_usage = UsageStats()

        try:
            # 确保BM25索引已构建
            if not self._bm25_built:
                logging.info("📦 BM25索引未构建，自动构建中...")
                self.build_bm25_index()

            # 1. 语义检索
            semantic_docs = self._search_with_filter(query, k=self.config.search_top_k * 3)
            if self._embedding_wrapper.last_usage:
                search_usage.embedding = search_usage.embedding + self._embedding_wrapper.last_usage
                self._embedding_wrapper.reset_usage()

            if not semantic_docs:
                return SearchResult(content="", documents=[], usage=search_usage)

            # 2. BM25检索
            bm25_results = self._bm25_search(query, top_k=self.config.search_top_k * 3)
            if not bm25_results:
                # BM25无结果，降级到纯语义检索
                logging.warning("⚠️ BM25检索无结果，使用纯语义检索")
                content = self._format_search_results(semantic_docs, expand_context)
                return SearchResult(
                    content=content,
                    documents=semantic_docs,
                    usage=search_usage,
                )

            # 3. RRF (Reciprocal Rank Fusion) 融合
            import hashlib
            from collections import defaultdict

            def get_doc_id(doc):
                return hashlib.md5(doc.page_content.encode()).hexdigest()

            doc_scores = defaultdict(float)

            # 语义检索得分
            for rank, doc in enumerate(semantic_docs):
                doc_id = get_doc_id(doc)
                doc_scores[doc_id] += semantic_weight / (1 + rank)

            # BM25检索得分
            for rank, (doc, score) in enumerate(bm25_results):
                doc_id = get_doc_id(doc)
                doc_scores[doc_id] += bm25_weight / (1 + rank)

            # 按得分排序
            all_docs_dict = {}
            for doc in semantic_docs:
                doc_id = get_doc_id(doc)
                all_docs_dict[doc_id] = doc
            for doc, _ in bm25_results:
                doc_id = get_doc_id(doc)
                all_docs_dict[doc_id] = doc

            sorted_doc_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)

            # Small2Big 模式下多取一些 child chunks，避免去重后结果不足
            sample_doc = all_docs_dict.get(sorted_doc_ids[0]) if sorted_doc_ids else None
            is_small2big = sample_doc and sample_doc.metadata.get("parent_chunk_id")
            fetch_count = self.config.search_top_k * 3 if is_small2big else self.config.search_top_k
            final_docs = [all_docs_dict[doc_id] for doc_id in sorted_doc_ids[:fetch_count]]

            # 4. Rerank 重排序（可选）
            if self._reranker and final_docs:
                try:
                    top_n = self.config.rerank.top_n or (self.config.search_top_k * 3 if is_small2big else self.config.search_top_k)
                    final_docs = self._reranker.rerank_documents(
                        query, final_docs, top_n=top_n
                    )
                    if self._reranker.last_usage:
                        search_usage.rerank = search_usage.rerank + self._reranker.last_usage
                        self._reranker.reset_usage()
                    logging.info(f"✅ Rerank 完成，保留 {len(final_docs)} 个文档")
                except Exception as e:
                    logging.warning(f"⚠️ Rerank 失败，使用原始排序: {e}")

            content = self._format_search_results(final_docs, expand_context)
            return SearchResult(
                content=content,
                documents=final_docs,
                usage=search_usage,
                metadata={
                    "semantic_weight": semantic_weight,
                    "bm25_weight": bm25_weight,
                    "doc_count": len(final_docs),
                },
            )

        except Exception as e:
            logging.error(f"❌ BM25混合检索失败: {e}")
            # 降级到纯语义检索
            semantic_docs = self._search_with_filter(query, k=self.config.search_top_k)
            content = self._format_search_results(semantic_docs, expand_context)
            return SearchResult(
                content=content,
                documents=semantic_docs,
                usage=search_usage,
            )

    def _format_search_results(self, docs: List, expand_context: bool) -> str:
        """
        格式化检索结果（提取为独立方法以便复用）

        支持两种上下文扩展模式:
        - Small2Big: 使用 parent_text 替代 child chunk 内容，通过 parent_chunk_id 去重
        - Legacy: 使用 prev_buffer/next_buffer 拼接前后文标记

        Args:
            docs: 文档列表
            expand_context: 是否扩展上下文

        Returns:
            格式化后的结果字符串
        """
        if not docs:
            return ""

        final_results = []
        seen_parent_ids = set()

        for doc in docs:
            content = doc.page_content.strip()
            parent_text = doc.metadata.get("parent_text", "")

            # Small2Big: 使用 parent_text 作为扩展上下文
            if expand_context and parent_text:
                parent_chunk_id = doc.metadata.get("parent_chunk_id", "")
                if parent_chunk_id and parent_chunk_id in seen_parent_ids:
                    continue  # 同一 parent 已输出过，跳过
                if parent_chunk_id:
                    seen_parent_ids.add(parent_chunk_id)
                full_text = parent_text
            elif expand_context:
                # Legacy 回退: 使用 buffer 标记
                prev_buffer = doc.metadata.get("prev_buffer", "")
                next_buffer = doc.metadata.get("next_buffer", "")
                parts = []
                if prev_buffer:
                    parts.append(f" [...前文: {prev_buffer}...]")
                parts.append(content)
                if next_buffer:
                    parts.append(f" [>>接下文: {next_buffer}...]")
                full_text = "".join(parts)
            else:
                full_text = content

            # 构建引用头信息
            source_name = doc.metadata.get("file_name", "Unknown")
            heading = doc.metadata.get("heading", "")
            content_type = doc.metadata.get("content_type", "")

            header_parts = [f"来源: {source_name}"]
            if heading:
                header_parts.append(f"章节: {heading}")
            if content_type and content_type != "text":
                header_parts.append(f"类型: {content_type}")

            result_item = (
                f"--- [{' | '.join(header_parts)}] ---\n"
                f"{full_text}\n"
            )
            final_results.append(result_item)

        return "\n".join(final_results)

    # ========================================================
    # 内部类：自定义BM25实现（当rank_bm25不可用时）
    # ========================================================

    class _CustomBM25:
        """
        自定义BM25实现（当rank_bm25库不可用时）

        BM25公式:
        score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1 + 1)) / (f(qi,D) + k1 * (1 - b + b * |D| / avgdl))
        """

        def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75, epsilon: float = 0.25):
            """
            初始化自定义BM25

            Args:
                corpus: 分词后的文档语料库
                k1: 词频饱和参数
                b: 长度归一化参数
                epsilon: IDF平滑参数
            """
            self.k1 = k1
            self.b = b
            self.epsilon = epsilon
            self.corpus = corpus

            # 计算文档长度
            self.doc_lens = [len(doc) for doc in corpus]

            # 计算平均文档长度
            self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0

            # 初始化TF、DF、IDF
            self.tf = []  # 每个文档的词频字典
            self.df = defaultdict(int)  # 文档频率

            self._initialize()

        def _initialize(self):
            """初始化TF、DF、IDF"""
            for doc in self.corpus:
                # 计算每个文档的词频
                tf_dict = defaultdict(int)
                for word in doc:
                    tf_dict[word] += 1

                self.tf.append(tf_dict)

                # 更新文档频率
                for word in tf_dict.keys():
                    self.df[word] += 1

        def get_scores(self, query: List[str]) -> List[float]:
            """
            计算查询对所有文档的BM25分数

            Args:
                query: 分词后的查询

            Returns:
                每个文档的分数列表
            """
            import math

            scores = []

            for i, doc in enumerate(self.corpus):
                score = 0
                doc_len = self.doc_lens[i]

                for word in query:
                    if word not in self.tf[i]:
                        continue

                    # 词频
                    freq = self.tf[i][word]

                    # IDF
                    N = len(self.corpus)
                    df = self.df.get(word, 0)
                    idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

                    # BM25分数
                    numerator = freq * (self.k1 + 1)
                    denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                    score += idf * (numerator / denominator)

                scores.append(score)

            return scores


__all__ = ["RAGService", "delete_document", "restore_document"]



# ====================== 测试代码 ======================
# 见test_simple.py
