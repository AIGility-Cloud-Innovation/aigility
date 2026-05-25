# markdown_splitter.py
"""
基于 Markdown AST 的智能切分器

核心优势:
1. 保持标题-内容的关联性
2. 表格、列表等结构化内容不会被破坏
3. 支持语义级别的切分
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document

try:
    from markdown_it import MarkdownIt
    from markdown_it.token import Token
    MARKDOWN_IT_AVAILABLE = True
except ImportError:
    MARKDOWN_IT_AVAILABLE = False
    raise ImportError(
        "markdown-it-py is required for AST-based splitting. "
        "Install it with: pip install markdown-it-py"
    )


class MarkdownASTSplitter:
    """
    基于 Markdown AST 的智能切分器

    特点:
    - 保持标题及其内容的关联性
    - 表格作为完整单元处理
    - 列表结构保持完整
    - 支持按 chunk_size 智能切分
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        length_function: callable = len,
        context_buffer_size: int = 100,
        min_chunk_size: int = 100,
        enable_small2big: bool = False,
        parent_chunk_size: int = 1024,
        child_chunk_size: int = 256,
        child_chunk_overlap: int = 64,
    ):
        """
        初始化切分器

        Args:
            chunk_size: 目标 chunk 大小（字符数）
            chunk_overlap: chunk 之间的重叠大小
            length_function: 计算文本长度的函数
            context_buffer_size: 上下文扩展时前后 buffer 的大小（字符数）
            min_chunk_size: 最小 chunk 大小，避免生成太小的 chunk
            enable_small2big: 是否启用 small2big 两层分块
            parent_chunk_size: 父块目标大小（字符数）
            child_chunk_size: 子块目标大小（字符数）
            child_chunk_overlap: 子块之间的重叠大小（字符数）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        self.context_buffer_size = context_buffer_size
        self.min_chunk_size = min_chunk_size
        self.enable_small2big = enable_small2big
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.child_chunk_overlap = child_chunk_overlap

        # 初始化 markdown-it 解析器，启用表格插件
        self.md = MarkdownIt().enable('table')

    def split_text(self, text: str) -> List[str]:
        """
        将 Markdown 文本切分为语义完整的 chunks

        Args:
            text: Markdown 格式的文本

        Returns:
            切分后的文本列表
        """
        results = self.split_text_structured(text)
        return [r['text'] for r in results]

    def split_text_structured(self, text: str) -> List[Dict[str, Any]]:
        """
        将 Markdown 文本切分为结构化 chunks

        Args:
            text: Markdown 格式的文本

        Returns:
            结构化切分结果列表，每个元素包含:
            - text: 切分后的文本
            - content_type: 内容类型 (text/table/code)
            - heading: 所属标题
            - section_path: 面包屑路径
            - block_types: 包含的 block 类型列表
        """
        if not text or not text.strip():
            return []

        tokens = self.md.parse(text)
        blocks = self._tokens_to_blocks(tokens)
        return self._merge_blocks(blocks)

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        切分文档列表，保持元数据

        Args:
            documents: 文档列表

        Returns:
            切分后的文档列表
        """
        result = []
        for doc in documents:
            chunks = self.split_text_structured(doc.page_content)
            chunk_texts = [c['text'] for c in chunks]

            for i, chunk_data in enumerate(chunks):
                # 前 buffer: 前一个 chunk 的末尾
                prev_buffer = ""
                if i > 0:
                    prev_buffer = chunk_texts[i - 1][-self.context_buffer_size:]

                # 后 buffer: 后一个 chunk 的开头
                next_buffer = ""
                if i < len(chunk_texts) - 1:
                    next_buffer = chunk_texts[i + 1][:self.context_buffer_size]

                result.append(Document(
                    page_content=chunk_data['text'],
                    metadata={
                        **doc.metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "content_type": chunk_data['content_type'],
                        "heading": chunk_data['heading'],
                        "section_path": chunk_data['section_path'],
                        "prev_buffer": prev_buffer,
                        "next_buffer": next_buffer,
                    }
                ))
        return result

    # ========================================================
    # Small2Big: 两层分块
    # ========================================================

    def split_text_structured_small2big(self, text: str) -> List[Dict[str, Any]]:
        """
        Small2Big 两层分块：先生成 parent chunks，再拆成 child chunks

        Phase 1: 用 parent_chunk_size 上限合并 AST blocks -> parent chunks
        Phase 2: 每个 parent chunk 按 child_chunk_size 拆成 child chunks

        Returns:
            每个 child chunk dict 包含:
            - text: child chunk 文本
            - parent_text: 完整 parent chunk 文本
            - parent_index: parent chunk 在文档中的索引
            - child_index: child 在 parent 中的索引
            - total_children_in_parent: parent 被拆成的 child 总数
            - content_type, heading, section_path, block_types: 继承自 parent
        """
        if not text or not text.strip():
            return []

        # Phase 1: 生成 parent chunks
        tokens = self.md.parse(text)
        blocks = self._tokens_to_blocks(tokens)
        parent_chunks = self._merge_blocks(blocks, max_size=self.parent_chunk_size)

        # Phase 2: 每个 parent chunk 拆成 child chunks
        all_children = []
        for parent_idx, parent in enumerate(parent_chunks):
            parent_text = parent['text']
            content_type = parent['content_type']

            # 表格和代码块不拆分，整个作为单个 child
            if content_type in ('table', 'code') or len(parent_text) <= self.child_chunk_size:
                all_children.append({
                    'text': parent_text,
                    'parent_text': parent_text,
                    'parent_index': parent_idx,
                    'child_index': 0,
                    'total_children_in_parent': 1,
                    'content_type': content_type,
                    'heading': parent['heading'],
                    'section_path': parent['section_path'],
                    'block_types': parent['block_types'],
                })
            else:
                # 按句子边界拆分 parent 文本
                child_texts = self._split_text_to_children(parent_text)
                for child_idx, child_text in enumerate(child_texts):
                    all_children.append({
                        'text': child_text,
                        'parent_text': parent_text,
                        'parent_index': parent_idx,
                        'child_index': child_idx,
                        'total_children_in_parent': len(child_texts),
                        'content_type': content_type,
                        'heading': parent['heading'],
                        'section_path': parent['section_path'],
                        'block_types': parent['block_types'],
                    })

        return all_children

    def _split_text_to_children(self, text: str) -> List[str]:
        """
        将文本按句子边界拆分为 child chunks

        使用 child_chunk_size 和 child_chunk_overlap 参数。
        """
        # 按句子切分（中英文标点）
        sentences = re.split(r'(?<=[。！？；.!?;])', text)
        sentences = [s for s in sentences if s.strip()]

        if not sentences:
            return [text]

        children = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = self.length_function(sentence)

            if current_size + sentence_size <= self.child_chunk_size:
                current_chunk.append(sentence)
                current_size += sentence_size
            else:
                if current_chunk:
                    children.append(''.join(current_chunk))
                # 开始新 chunk，带 overlap
                if self.child_chunk_overlap > 0 and current_chunk:
                    overlap_text = ''.join(current_chunk)[-self.child_chunk_overlap:]
                    current_chunk = [overlap_text, sentence]
                    current_size = self.length_function(overlap_text) + sentence_size
                else:
                    current_chunk = [sentence]
                    current_size = sentence_size

        if current_chunk:
            children.append(''.join(current_chunk))

        return children if children else [text]

    def split_documents_small2big(self, documents: List[Document]) -> List[Document]:
        """
        Small2Big 版本的文档切分

        为每个 child chunk 创建 Document 对象，metadata 中包含 parent_text。
        不包含 prev_buffer/next_buffer。
        """
        result = []
        global_child_index = 0

        for doc in documents:
            chunks = self.split_text_structured_small2big(doc.page_content)

            for chunk_data in chunks:
                result.append(Document(
                    page_content=chunk_data['text'],
                    metadata={
                        **doc.metadata,
                        "chunk_index": global_child_index,
                        "parent_text": chunk_data['parent_text'],
                        "parent_index": chunk_data['parent_index'],
                        "child_index": chunk_data['child_index'],
                        "total_children_in_parent": chunk_data['total_children_in_parent'],
                        "content_type": chunk_data['content_type'],
                        "heading": chunk_data['heading'],
                        "section_path": chunk_data['section_path'],
                    }
                ))
                global_child_index += 1

        # 回填 total_chunks
        for doc in result:
            doc.metadata["total_chunks"] = global_child_index

        return result

    def _tokens_to_blocks(self, tokens: List[Token]) -> List[Dict[str, Any]]:
        """
        将 token 列表转换为结构化块

        每个块包含:
        - type: 块类型 (heading, table, list, paragraph, etc.)
        - content: 块内容
        - level: 标题级别 (如果是 heading)
        """
        blocks = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # 处理标题
            if token.type == 'heading_open':
                level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
                # 下一个 token 是标题内容
                content_token = tokens[i + 1] if i + 1 < len(tokens) else None
                content = content_token.content if content_token else ''
                blocks.append({
                    'type': 'heading',
                    'level': level,
                    'content': f"{'#' * level} {content}",
                    'raw_content': content,
                })
                i += 3  # heading_open, inline, heading_close
                continue

            # 处理表格
            if token.type == 'table_open':
                table_tokens = []
                while i < len(tokens) and tokens[i].type != 'table_close':
                    table_tokens.append(tokens[i])
                    i += 1
                table_content = self._extract_table_content(table_tokens)
                if table_content:
                    blocks.append({
                        'type': 'table',
                        'content': table_content,
                    })
                i += 1  # 跳过 table_close
                continue

            # 处理列表
            if token.type in ('bullet_list_open', 'ordered_list_open'):
                list_tokens = []
                close_type = 'bullet_list_close' if token.type == 'bullet_list_open' else 'ordered_list_close'
                while i < len(tokens) and tokens[i].type != close_type:
                    list_tokens.append(tokens[i])
                    i += 1
                list_content = self._extract_list_content(list_tokens)
                if list_content:
                    blocks.append({
                        'type': 'list',
                        'content': list_content,
                    })
                i += 1  # 跳过 close token
                continue

            # 处理代码块
            if token.type == 'fence':
                code_content = token.content
                lang = token.info or ''
                blocks.append({
                    'type': 'code',
                    'content': f"```{lang}\n{code_content}\n```" if lang else f"```\n{code_content}\n```",
                })
                i += 1
                continue

            # 处理普通段落
            if token.type == 'paragraph_open':
                # 收集段落内容
                paragraph_tokens = []
                while i < len(tokens) and tokens[i].type != 'paragraph_close':
                    if tokens[i].content:
                        paragraph_tokens.append(tokens[i].content)
                    i += 1
                content = ' '.join(paragraph_tokens)
                if content:
                    blocks.append({
                        'type': 'paragraph',
                        'content': content,
                    })
                i += 1
                continue

            # 处理水平线
            if token.type == 'hr':
                blocks.append({
                    'type': 'hr',
                    'content': '---',
                })
                i += 1
                continue

            # 默认：跳过其他 token
            i += 1

        return blocks

    def _extract_table_content(self, tokens: List[Token]) -> Optional[str]:
        """从 token 列表中提取表格内容"""
        rows = []
        current_row = []

        for token in tokens:
            if token.type == 'tr_open':
                current_row = []
            elif token.type == 'tr_close':
                if current_row:
                    rows.append(current_row)
            elif token.type == 'inline':
                # 提取单元格内容
                content = token.content.strip()
                if content:
                    current_row.append(content)

        if not rows:
            return None

        # 转换为 Markdown 表格格式
        # 第一行作为表头
        header = rows[0]
        table_lines = ['| ' + ' | '.join(header) + ' |']
        table_lines.append('| ' + ' | '.join(['---'] * len(header)) + ' |')

        # 添加数据行
        for row in rows[1:]:
            # 确保行数与表头一致
            while len(row) < len(header):
                row.append('')
            table_lines.append('| ' + ' | '.join(row) + ' |')

        return '\n'.join(table_lines)

    def _extract_list_content(self, tokens: List[Token]) -> Optional[str]:
        """从 token 列表中提取列表内容"""
        items = []
        current_item = []
        is_ordered = False

        for token in tokens:
            if token.type == 'list_item_open':
                current_item = []
            elif token.type == 'list_item_close':
                if current_item:
                    items.append(' '.join(current_item))
            elif token.type == 'inline' and token.content:
                # 根据列表类型添加前缀
                prefix = '- ' if not is_ordered else '1. '
                current_item.append(f"{prefix}{token.content}")
            elif token.type == 'bullet_list_open':
                is_ordered = False
            elif token.type == 'ordered_list_open':
                is_ordered = True

        return '\n'.join(items) if items else None

    def _merge_blocks(self, blocks: List[Dict[str, Any]], max_size: int = None) -> List[Dict[str, Any]]:
        """
        合并小块，确保每个 chunk 不超过 max_size

        返回结构化结果，每个 chunk 包含:
        - text: 合并后的文本
        - content_type: 主要内容类型 (text/table/code)
        - heading: 当前所属标题
        - section_path: 面包屑路径
        - block_types: 该 chunk 包含的所有 block 类型

        Args:
            blocks: 解析后的 block 列表
            max_size: 最大 chunk 大小，默认使用 self.chunk_size
        """
        if not blocks:
            return []

        if max_size is None:
            max_size = self.chunk_size

        results = []
        current_chunk_texts = []
        current_block_types = []
        current_size = 0
        heading_stack = []  # [(level, raw_content), ...]
        # 记录当前 chunk 开始时的标题上下文
        chunk_heading = ""
        chunk_section_path = ""

        def _detect_content_type(block_types):
            """根据 block 类型列表判断主要 content_type"""
            if 'table' in block_types:
                return 'table'
            if 'code' in block_types:
                return 'code'
            return 'text'

        def _save_chunk():
            """保存当前 chunk 到 results"""
            if current_chunk_texts:
                results.append({
                    'text': '\n\n'.join(current_chunk_texts),
                    'content_type': _detect_content_type(current_block_types),
                    'heading': chunk_heading,
                    'section_path': chunk_section_path,
                    'block_types': list(current_block_types),
                })

        def _start_new_chunk():
            """重置当前 chunk 状态"""
            nonlocal current_chunk_texts, current_block_types, current_size
            current_chunk_texts = []
            current_block_types = []
            current_size = 0

        def _capture_heading():
            """捕获当前标题上下文到 chunk 级别变量"""
            nonlocal chunk_heading, chunk_section_path
            if heading_stack:
                chunk_heading = heading_stack[-1][1]
                chunk_section_path = " > ".join(h[1] for h in heading_stack)
            else:
                chunk_heading = ""
                chunk_section_path = ""

        i = 0
        while i < len(blocks):
            block = blocks[i]
            block_content = block['content']
            block_size = self.length_function(block_content)
            block_type = block['type']

            # 检查是否是标题块
            is_heading = block_type == 'heading'

            # 如果是标题，尝试将后续内容合并
            if is_heading and i + 1 < len(blocks):
                # 先更新标题层级
                level = block['level']
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, block['raw_content']))

                next_block = blocks[i + 1]
                next_content = next_block['content']
                next_size = self.length_function(next_content)

                combined_size = current_size + block_size + 1 + next_size

                if combined_size <= max_size:
                    if not current_chunk_texts:
                        _capture_heading()
                    combined_content = f"{block_content}\n\n{next_content}"
                    current_chunk_texts.append(combined_content)
                    current_block_types.append(block_type)
                    current_block_types.append(next_block['type'])
                    current_size += block_size + 1 + next_size
                    i += 2
                    continue
                else:
                    if current_chunk_texts:
                        _save_chunk()
                        _start_new_chunk()
                    _capture_heading()
                    combined_content = f"{block_content}\n\n{next_content}"
                    current_chunk_texts.append(combined_content)
                    current_block_types.append(block_type)
                    current_block_types.append(next_block['type'])
                    current_size = block_size + 1 + next_size
                    i += 2
                    continue

            # 检查当前块是否能加入当前 chunk
            if current_size + block_size <= max_size:
                if not current_chunk_texts:
                    _capture_heading()
                current_chunk_texts.append(block_content)
                current_block_types.append(block_type)
                current_size += block_size
                i += 1
            else:
                # 当前 chunk 已满
                if current_size < self.min_chunk_size and i + 1 < len(blocks):
                    if not current_chunk_texts:
                        _capture_heading()
                    current_chunk_texts.append(block_content)
                    current_block_types.append(block_type)
                    current_size += block_size
                    i += 1
                    continue

                # 保存当前 chunk
                if current_chunk_texts:
                    _save_chunk()
                    # 保留 overlap
                    if self.chunk_overlap > 0 and current_chunk_texts:
                        overlap_text = current_chunk_texts[-1]
                        overlap_size = self.length_function(overlap_text)
                        if overlap_size <= self.chunk_overlap:
                            current_chunk_texts = [overlap_text]
                            current_size = overlap_size
                        else:
                            overlap_text = overlap_text[-self.chunk_overlap:]
                            current_chunk_texts = [overlap_text]
                            current_size = self.chunk_overlap
                    else:
                        current_chunk_texts = []
                        current_size = 0
                    current_block_types = []

                # 如果单个块超过 chunk_size，需要切分
                if block_size > max_size:
                    if block_type in ('table', 'list'):
                        _capture_heading()
                        current_chunk_texts = [block_content]
                        current_block_types = [block_type]
                        current_size = block_size
                    else:
                        _capture_heading()
                        sub_chunks = self._split_large_block(block_content, max_size)
                        for sc in sub_chunks[:-1]:
                            results.append({
                                'text': sc,
                                'content_type': _detect_content_type([block_type]),
                                'heading': chunk_heading,
                                'section_path': chunk_section_path,
                                'block_types': [block_type],
                            })
                        current_chunk_texts = [sub_chunks[-1]] if sub_chunks else []
                        current_block_types = [block_type] if sub_chunks else []
                        current_size = self.length_function(sub_chunks[-1]) if sub_chunks else 0
                else:
                    _capture_heading()
                    current_chunk_texts = [block_content]
                    current_block_types = [block_type]
                    current_size = block_size

                i += 1

        # 保存最后一个 chunk
        _save_chunk()

        return results

    def _split_large_block(self, content: str, max_size: int = None) -> List[str]:
        """切分超过 max_size 的大块"""
        if max_size is None:
            max_size = self.chunk_size
        chunks = []
        current_chunk = []
        current_size = 0

        # 按句子切分
        sentences = re.split(r'([。！？；])', content)

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # 加上标点

            sentence_size = self.length_function(sentence)

            if current_size + sentence_size <= max_size:
                current_chunk.append(sentence)
                current_size += sentence_size
            else:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = sentence_size
                else:
                    # 单个句子就超过 max_size，强制切分
                    chunks.append(sentence[:max_size])
                    if sentence[max_size:]:
                        current_chunk = [sentence[max_size:]]
                        current_size = self.length_function(sentence[max_size:])

        if current_chunk:
            chunks.append(''.join(current_chunk))

        return chunks if chunks else [content]


__all__ = ["MarkdownASTSplitter"]
