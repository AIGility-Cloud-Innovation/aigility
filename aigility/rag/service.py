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

    def add_file(self, file_path: str) -> Dict[str, str]:
            """
            加载文件 -> 智能解析 -> 注入上下文元数据 -> 存入向量库

            Args:
                file_path: 文件路径

            Returns:
                包含文件信息的字典：
                {
                    "file_hash": str,     # 基于文件内容的MD5哈希（用于删除操作）
                    "file_name": str      # 文件名（用于删除操作）
                }

            注意：
                - 返回的 file_hash 可用于后续的 delete_document 和 restore_document 操作
                - 相同内容的文件会有相同的 file_hash
                - 使用 file_hash 删除时会删除所有相同内容的文件
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
                if hasattr(self.vector_store, "get"):
                    vector_store_type = self.config.vector_store.provider

                    if vector_store_type == "chroma":
                        # Chroma: 查找所有相同 file_hash 的文件
                        existing_with_same_hash = self.vector_store.get(
                            where={"file_hash": file_hash},
                            limit=1
                        )
                    elif vector_store_type == "qdrant":
                        # Qdrant: 查找所有相同 file_hash 的文件
                        existing_with_same_hash = self.vector_store.get(
                            where={"metadata.file_hash": file_hash},
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
                        logging.info(f"♻️ 检测到相同内容的已删除文件，恢复中: {doc_name} (hash: {file_hash})")
                        success = self.restore_document(file_hash=file_hash)

                        if success:
                            # 更新文件名为新上传的文件名
                            logging.info(f"📝 更新文件名: {doc_name}")
                            self._update_chunks_metadata(
                                file_hash=file_hash,
                                metadata_update={"file_name": doc_name}
                            )
                            return {
                                "file_hash": file_hash,
                                "file_name": doc_name
                            }
                        else:
                            logging.warning(f"⚠️ 恢复文件失败，将作为新文件添加: {doc_name}")
                    else:
                        # 文件未删除：仅更新文件名（如果不同）
                        logging.info(f"✅ 文件已存在且未被删除，更新文件名: {doc_name} (hash: {file_hash})")
                        self._update_chunks_metadata(
                            file_hash=file_hash,
                            metadata_update={"file_name": doc_name}
                        )
                        return {
                            "file_hash": file_hash,
                            "file_name": doc_name
                        }

                logging.info(f"📄 Processing file: {doc_name}")
                chunks = self.ingestion.process_documents(file_path)

                if not chunks:
                    return {
                        "file_hash": file_hash,
                        "file_name": doc_name
                    }

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
                    chunk.metadata["is_deleted"] = False  # 软删除标记
                    
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

                # 返回文件信息，用于后续操作
                return {
                    "file_hash": file_hash,
                    "file_name": doc_name
                }

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
            # 1. 基础检索 - 添加过滤条件只检索未删除的chunk
            docs = self._search_with_filter(query, k=self.config.search_top_k)
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

__all__ = ["RAGService", "delete_document", "restore_document"]


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
    print(f"   - Embedding: {config.embedding.provider} / {config.embedding.model_name} / {config.embedding.api_key}")
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