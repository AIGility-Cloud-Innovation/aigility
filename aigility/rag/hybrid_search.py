# rag_enhanced_search.py
# 增强的检索功能：混合检索 + 查询优化

import logging
from typing import List, Optional
from collections import defaultdict


class EnhancedSearch:
    """增强的检索功能"""

    def __init__(self, vector_store):
        """
        初始化增强检索

        Args:
            vector_store: 向量数据库实例
        """
        self.vector_store = vector_store
        self._bm25_index = None
        self._bm25_corpus = None
        self._bm25_metadata = None

    def _parse_multi_query(self, query: str) -> List[str]:
        """
        解析多组查询（用 ||| 分隔的查询）

        例如："市场|||价格|||定位" -> ["市场", "价格", "定位"]
        """
        if "|||" in query:
            # 分割并去重
            sub_queries = [q.strip() for q in query.split("|||")]
            # 去除空字符串
            sub_queries = [q for q in sub_queries if q]
            return sub_queries
        return [query]

    def _expand_query(self, query: str) -> List[str]:
        """
        查询扩展：将空格分隔的同义词展开

        例如："目标市场 市场范围" -> ["目标市场", "市场范围", "目标市场 市场范围"]
        """
        terms = query.strip().split()
        if len(terms) <= 1:
            return [query]

        expanded_queries = [query]  # 原始查询
        # 添加单个词
        expanded_queries.extend(terms)
        # 添加两个词的组合
        for i in range(len(terms) - 1):
            expanded_queries.append(f"{terms[i]} {terms[i+1]}")

        return list(set(expanded_queries))  # 去重

    def _keyword_search(self, query: str, docs: List, top_k: int = 5) -> List:
        """
        关键词搜索：基于文档内容的简单关键词匹配

        Args:
            query: 查询词
            docs: 候选文档列表
            top_k: 返回数量

        Returns:
            按关键词匹配度排序的文档列表
        """
        # 解析查询词
        keywords = query.strip().split()

        # 计算每个文档的关键词匹配分数
        scored_docs = []
        for doc in docs:
            content = doc.page_content.lower()
            score = 0
            for kw in keywords:
                if kw.lower() in content:
                    score += content.count(kw.lower()) * 10  # 每次出现加10分
                    # 如果是精确匹配（完整词），额外加分
                    if f" {kw.lower()} " in f" {content} ":
                        score += 5

            if score > 0:
                scored_docs.append((doc, score))

        # 按分数排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 返回前 top_k 个文档
        return [doc for doc, score in scored_docs[:top_k]]

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        use_keyword: bool = True,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List:
        """
        混合检索：结合语义检索和关键词检索

        Args:
            query: 查询文本（支持 ||| 分隔的多查询）
            k: 返回结果数量
            use_keyword: 是否启用关键词检索
            semantic_weight: 语义检索权重（0-1）
            keyword_weight: 关键词检索权重（0-1）

        Returns:
            检索结果列表
        """
        try:
            # ========================================================
            # 步骤1：解析查询
            # ========================================================
            sub_queries = self._parse_multi_query(query)

            # 如果有多组查询，对每组进行扩展
            all_queries = []
            for sq in sub_queries:
                expanded = self._expand_query(sq)
                all_queries.extend(expanded)

            logging.info(f"🔍 解析查询: {query} -> {len(all_queries)} 个扩展查询")

            # ========================================================
            # 步骤2：语义检索（Vector Search）
            # ========================================================
            # 对每个扩展查询进行语义检索
            semantic_results = []
            seen_ids = set()  # 去重

            for q in all_queries[:3]:  # 限制最多3个查询，避免性能问题
                try:
                    results = self.vector_store.similarity_search(q, k=k * 2)
                    for doc in results:
                        # 使用文档内容作为唯一标识去重
                        doc_id = doc.page_content[:100]
                        if doc_id not in seen_ids:
                            seen_ids.add(doc_id)
                            semantic_results.append(doc)
                except Exception as e:
                    logging.warning(f"⚠️ 查询 '{q}' 检索失败: {e}")

            # 如果没有检索到结果，返回空列表
            if not semantic_results:
                return []

            # ========================================================
            # 步骤3：关键词检索（Keyword Search）
            # ========================================================
            keyword_results = []
            if use_keyword:
                # 合并所有查询词用于关键词搜索
                combined_query = " ".join(sub_queries)
                keyword_results = self._keyword_search(
                    combined_query,
                    semantic_results,  # 在语义检索结果中进行关键词过滤
                    top_k=k * 2
                )

            # ========================================================
            # 步骤4：融合结果（Reciprocal Rank Fusion）
            # ========================================================
            # RRF 算法：综合多个排序结果
            # 公式：score = sum(weight / (k + rank))

            all_docs = list(set(semantic_results + keyword_results))
            doc_scores = defaultdict(float)

            # 语义检索得分
            for rank, doc in enumerate(semantic_results):
                doc_id = doc.page_content[:100]
                doc_scores[doc_id] += semantic_weight / (1 + rank)

            # 关键词检索得分
            if use_keyword and keyword_results:
                for rank, doc in enumerate(keyword_results):
                    doc_id = doc.page_content[:100]
                    doc_scores[doc_id] += keyword_weight / (1 + rank)

            # 按综合得分排序
            sorted_docs = sorted(
                all_docs,
                key=lambda d: doc_scores[d.page_content[:100]],
                reverse=True
            )

            return sorted_docs[:k]

        except Exception as e:
            logging.error(f"❌ 混合检索失败: {e}")
            # 降级：使用原始查询的语义检索
            return self.vector_store.similarity_search(query.split("|||")[0], k=k)


def enhanced_search_method(self, query: str, expand_context: bool = True, use_hybrid: bool = True) -> str:
    """
    增强的检索方法（需要注入到 RAGService 中）

    Args:
        query: 查询文本
        expand_context: 是否扩展上下文
        use_hybrid: 是否使用混合检索

    Returns:
        检索结果字符串
    """
    try:
        if use_hybrid:
            # 使用混合检索
            enhanced_search = EnhancedSearch(self.vector_store)
            docs = enhanced_search.hybrid_search(
                query,
                k=self.config.search_top_k,
                use_keyword=True,
                semantic_weight=0.7,
                keyword_weight=0.3
            )
        else:
            # 使用原有的检索方法
            docs = self._search_with_filter(query, k=self.config.search_top_k)

        if not docs:
            return ""

        # ========================================================
        # 结果格式化（支持 Small2Big 和 Legacy 两种模式）
        # ========================================================
        final_results = []
        seen_parent_ids = set()

        for doc in docs:
            content = doc.page_content.strip()
            parent_text = doc.metadata.get("parent_text", "")

            # Small2Big: 使用 parent_text 作为扩展上下文
            if expand_context and parent_text:
                parent_chunk_id = doc.metadata.get("parent_chunk_id", "")
                if parent_chunk_id and parent_chunk_id in seen_parent_ids:
                    continue
                if parent_chunk_id:
                    seen_parent_ids.add(parent_chunk_id)
                full_text = parent_text
            elif expand_context:
                # Legacy 回退
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

    except Exception as e:
        logging.error(f"❌ Enhanced search failed: {str(e)}")
        # 降级策略
        return "\n".join([d.page_content for d in docs])


# 为方便使用，提供一个 monkey patch 函数
def patch_rag_service():
    """
    将增强检索方法注入到 RAGService 中

    使用方法：
    >>> from aigility.rag.hybrid_search import patch_rag_service
    >>> patch_rag_service()
    >>> service = RAGService()
    >>> result = service.search_enhanced("市场|||价格", use_hybrid=True)
    """
    from aigility.rag.service import RAGService
    RAGService.search_enhanced = enhanced_search_method
    RAGService._get_enhanced_search = lambda self: EnhancedSearch(self.vector_store)
    logging.info("✅ 已注入增强检索方法到 RAGService")


if __name__ == "__main__":
    # 测试代码
    import os
    from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig
    from aigility.rag.service import RAGService

    # 注入增强方法
    patch_rag_service()

    # 配置
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
        search_top_k=5
    )

    # 初始化服务
    service = RAGService(config=config)

    # 测试检索
    test_queries = [
        "销售市场 目标市场 市场范围 销售地区|||价格定位 定价策略 价格区间 价位 定价",
        "目标市场",
        "北美 欧洲 Amazon",
        "价格 定价"
    ]

    print("=" * 60)
    print("🧪 增强检索测试")
    print("=" * 60)

    for query in test_queries:
        print(f"\n🔍 Q: {query}")

        # 原始检索
        print("\n--- 原始检索 ---")
        result_old = service.search(query, expand_context=False)
        if result_old:
            print(result_old[:300])
        else:
            print("(无结果)")

        # 增强检索
        print("\n--- 增强检索 ---")
        result_new = service.search_enhanced(query, expand_context=False, use_hybrid=True)
        if result_new:
            print(result_new[:300])
        else:
            print("(无结果)")

    print("\n" + "=" * 60)
