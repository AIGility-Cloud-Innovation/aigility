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
    ):
        """
        初始化切分器

        Args:
            chunk_size: 目标 chunk 大小（字符数）
            chunk_overlap: chunk 之间的重叠大小
            length_function: 计算文本长度的函数
            context_buffer_size: 上下文扩展时前后 buffer 的大小（字符数）
            min_chunk_size: 最小 chunk 大小，避免生成太小的 chunk
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        self.context_buffer_size = context_buffer_size
        self.min_chunk_size = min_chunk_size

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
        if not text or not text.strip():
            return []

        # 解析 Markdown 为 AST
        tokens = self.md.parse(text)

        # 将 token 转换为结构化块
        blocks = self._tokens_to_blocks(tokens)

        # 合并小块，确保不超过 chunk_size
        chunks = self._merge_blocks(blocks)

        return chunks

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
            chunks = self.split_text(doc.page_content)

            # 计算每个 chunk 的前后 buffer
            for i, chunk in enumerate(chunks):
                # 前 buffer: 前一个 chunk 的末尾
                prev_buffer = ""
                if i > 0:
                    prev_chunk = chunks[i - 1]
                    prev_buffer = prev_chunk[-self.context_buffer_size:]

                # 后 buffer: 后一个 chunk 的开头
                next_buffer = ""
                if i < len(chunks) - 1:
                    next_chunk = chunks[i + 1]
                    next_buffer = next_chunk[:self.context_buffer_size]

                result.append(Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "prev_buffer": prev_buffer,
                        "next_buffer": next_buffer,
                    }
                ))
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

    def _merge_blocks(self, blocks: List[Dict[str, Any]]) -> List[str]:
        """
        合并小块，确保每个 chunk 不超过 chunk_size

        策略:
        1. 标题与其紧随的内容（段落、表格、列表）保持在一起
        2. 如果单个块超过 chunk_size，尝试进一步切分
        3. 保持 chunk_overlap 的重叠
        """
        if not blocks:
            return []

        chunks = []
        current_chunk = []
        current_size = 0

        i = 0
        while i < len(blocks):
            block = blocks[i]
            block_content = block['content']
            block_size = self.length_function(block_content)

            # 检查是否是标题块
            is_heading = block['type'] == 'heading'

            # 如果是标题，尝试将后续内容合并
            if is_heading and i + 1 < len(blocks):
                next_block = blocks[i + 1]
                next_content = next_block['content']
                next_size = self.length_function(next_content)

                # 检查合并后是否超过 chunk_size
                combined_size = current_size + block_size + 1 + next_size  # +1 for newline

                if combined_size <= self.chunk_size:
                    # 合并标题和下一个块
                    combined_content = f"{block_content}\n\n{next_content}"
                    current_chunk.append(combined_content)
                    current_size += block_size + 1 + next_size
                    i += 2  # 跳过下一个块
                    continue
                else:
                    # 标题+下一个块超过 chunk_size，但标题必须和内容保持在一起
                    # 先保存当前 chunk（如果有内容）
                    if current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    # 标题和下一个块强制合并（允许超过 chunk_size）
                    combined_content = f"{block_content}\n\n{next_content}"
                    current_chunk.append(combined_content)
                    current_size = block_size + 1 + next_size
                    i += 2  # 跳过下一个块
                    continue

            # 检查当前块是否能加入当前 chunk
            if current_size + block_size <= self.chunk_size:
                current_chunk.append(block_content)
                current_size += block_size
                i += 1
            else:
                # 当前 chunk 已满
                # 如果当前 chunk 太小，尝试和下一个 block 合并（避免小 chunk）
                if current_size < self.min_chunk_size and i + 1 < len(blocks):
                    current_chunk.append(block_content)
                    current_size += block_size
                    i += 1
                    continue

                # 保存当前 chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    # 保留 overlap
                    if self.chunk_overlap > 0 and current_chunk:
                        overlap_text = current_chunk[-1]
                        overlap_size = self.length_function(overlap_text)
                        if overlap_size <= self.chunk_overlap:
                            current_chunk = [overlap_text]
                            current_size = overlap_size
                        else:
                            # 从最后一个块中截取 overlap
                            overlap_text = overlap_text[-self.chunk_overlap:]
                            current_chunk = [overlap_text]
                            current_size = self.chunk_overlap
                    else:
                        current_chunk = []
                        current_size = 0

                # 如果单个块超过 chunk_size，需要切分
                if block_size > self.chunk_size:
                    # 表格/列表块不切分，保持结构完整（允许超过 chunk_size）
                    if block['type'] in ('table', 'list'):
                        current_chunk = [block_content]
                        current_size = block_size
                    else:
                        sub_chunks = self._split_large_block(block_content)
                        chunks.extend(sub_chunks[:-1])  # 除最后一个都直接添加
                        current_chunk = [sub_chunks[-1]] if sub_chunks else []
                        current_size = self.length_function(sub_chunks[-1]) if sub_chunks else 0
                else:
                    current_chunk = [block_content]
                    current_size = block_size

                i += 1

        # 保存最后一个 chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _split_large_block(self, content: str) -> List[str]:
        """切分超过 chunk_size 的大块"""
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

            if current_size + sentence_size <= self.chunk_size:
                current_chunk.append(sentence)
                current_size += sentence_size
            else:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = sentence_size
                else:
                    # 单个句子就超过 chunk_size，强制切分
                    chunks.append(sentence[:self.chunk_size])
                    if sentence[self.chunk_size:]:
                        current_chunk = [sentence[self.chunk_size:]]
                        current_size = self.length_function(sentence[self.chunk_size:])

        if current_chunk:
            chunks.append(''.join(current_chunk))

        return chunks if chunks else [content]


__all__ = ["MarkdownASTSplitter"]
