# ingestion.py
"""
文档解析与切分管理器

使用前需要安装相应的文档处理依赖:
- PDF: pip install pypdf
- Word: pip install docx2txt
- Markdown: pip install unstructured
- Excel: pip install unstructured openpyxl
"""

import os
import re
from typing import List, Dict, TYPE_CHECKING
from hashlib import md5

if TYPE_CHECKING:
    from langchain_core.documents import Document

from .config import IngestionConfig


class IngestionManager:
    """通用文档解析与切分管理器"""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self._splitter = None
        
        # 通用分层分隔符
        self.universal_separators = [
            r"\n#{1,6} ",          # Markdown 标题
            r"\n[一二三四五六七八九十]{1,2}、",  # 中文数字标题
            r"\n\d{1,2}[.、]",      # 阿拉伯数字标题
            r"\n\[.*?\]\n",        # 方括号标签
            "\n\n", "\r\r", "\n\r\n\r",  # 段落分隔符
            "\n", ". ", "。", "！", "？", "；", "：",  # 句子分隔符
            " ", "\t", "",  # 字符分隔符
        ]
        
        # 去重缓存
        self.duplicate_cache: Dict[str, set] = {}

    @property
    def splitter(self):
        """延迟初始化拆分器"""
        if self._splitter is None:
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                raise ImportError(
                    "使用文档切分功能需要安装: "
                    "pip install langchain-text-splitters"
                )
            
            self._splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                separators=self.universal_separators,
                length_function=len
            )
        return self._splitter

    def _get_loader(self, file_path: str):
        """通用文件加载器（延迟导入）"""
        ext = os.path.splitext(file_path)[-1].lower()
        
        # 延迟导入
        try:
            from langchain_community.document_loaders import (
                PyPDFLoader, TextLoader, UnstructuredMarkdownLoader,
                Docx2txtLoader, UnstructuredExcelLoader
            )
        except ImportError:
            raise ImportError(
                "使用文档加载功能需要安装: "
                "pip install langchain-community"
            )
        
        loader_map = {
            ".txt": TextLoader,
            ".pdf": PyPDFLoader,
            ".md": UnstructuredMarkdownLoader,
            ".docx": Docx2txtLoader,
            ".doc": Docx2txtLoader,
            ".xlsx": UnstructuredExcelLoader,
            ".xls": UnstructuredExcelLoader
        }
        
        if ext not in loader_map:
            raise ValueError(
                f"Unsupported file type: {ext}, "
                f"supported types: {list(loader_map.keys())}"
            )
        
        loader_cls = loader_map[ext]
        if ext == ".txt":
            return loader_cls(file_path, encoding="utf-8")
        else:
            return loader_cls(file_path)

    def load_file(self, file_path: str) -> List["Document"]:
        """加载文件，返回原始 Document 列表"""
        if not isinstance(file_path, str):
            raise TypeError(f"file_path must be str, got {type(file_path)}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if os.path.getsize(file_path) == 0:
            raise ValueError(f"Empty file: {file_path}")
        
        try:
            ext = os.path.splitext(file_path)[-1].lower()
            loader = self._get_loader(file_path)
            docs = loader.load()
            
            # 补充元数据
            for doc in docs:
                doc.metadata.update({
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "file_type": ext,
                    "original_page": doc.metadata.get("page", 0)
                })
            return docs
        except Exception as e:
            raise RuntimeError(f"Load file failed: {file_path}, error: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """文本清洗"""
        if not self.config.enable_text_cleaning:
            return text
        
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)
        text = re.sub(
            r"[^\u4e00-\u9fa5a-zA-Z0-9\s\.\,，。！？；：（）()【】《》、\-_=+*&^%$#@!~`·]",
            "",
            text
        )
        text = re.sub(r"([.。！？；：]){2,}", r"\1", text)
        text = re.sub(r"^\s+|\s+$", "", text)
        return text

    def _remove_duplicate(self, docs: List["Document"], file_key: str) -> List["Document"]:
        """去重"""
        if not self.config.enable_duplicate_removal:
            return docs
        
        if file_key not in self.duplicate_cache:
            self.duplicate_cache[file_key] = set()
        
        unique_docs = []
        for doc in docs:
            clean_text = self._clean_text(doc.page_content)
            if len(clean_text) < self.config.min_chunk_length:
                continue
            
            text_hash = md5(clean_text.encode("utf-8")).hexdigest()
            if text_hash not in self.duplicate_cache[file_key]:
                self.duplicate_cache[file_key].add(text_hash)
                doc.page_content = clean_text
                unique_docs.append(doc)
        
        return unique_docs

    def _split_and_trim(self, docs: List["Document"]) -> List["Document"]:
        """拆分+修剪"""
        split_docs = self.splitter.split_documents(docs)
        trimmed_docs = []
        
        for doc in split_docs:
            clean_text = self._clean_text(doc.page_content)
            if len(clean_text) < self.config.min_chunk_length:
                continue
            
            if len(clean_text) > self.config.max_chunk_length:
                last_sep_pos = -1
                for sep in self.universal_separators[-5:]:
                    pos = clean_text.rfind(sep, 0, self.config.max_chunk_length)
                    if pos > last_sep_pos:
                        last_sep_pos = pos
                if last_sep_pos != -1:
                    clean_text = clean_text[:last_sep_pos + len(sep)]
                else:
                    clean_text = clean_text[:self.config.max_chunk_length]
            
            doc.page_content = clean_text
            trimmed_docs.append(doc)
        
        return trimmed_docs

    def _add_universal_tag(self, docs: List["Document"]) -> List["Document"]:
        """添加结构化标签"""
        if not self.config.enable_structured_tag:
            return docs
        
        tagged_docs = []
        for idx, doc in enumerate(docs):
            file_type = doc.metadata.get("file_type", "unknown").strip(".")
            page_num = doc.metadata.get("original_page", "0")
            tag = f"【{file_type.upper()}-PAGE{page_num}-CHUNK{idx+1}】"
            
            title_match = re.search(
                r"^(#+.+?$|[\一二三四五六七八九十]{1,2}、.+?$|\d{1,2}[.、].+?$)",
                doc.page_content,
                re.MULTILINE
            )
            if title_match:
                title = title_match.group(0).strip()[:20]
                tag = f"{tag}【标题：{title}】"
            
            doc.page_content = f"{tag}\n{doc.page_content}"
            tagged_docs.append(doc)
        
        return tagged_docs

    def process_raw_docs(self, raw_docs: List["Document"], file_path: str) -> List["Document"]:
        """处理已加载的原始 Document 列表（供 RAGService 调用）"""
        if not raw_docs:
            return []
        
        # 1. 拆分+修剪
        split_docs = self._split_and_trim(raw_docs)
        
        # 2. 去重
        file_key = md5(file_path.encode("utf-8")).hexdigest()
        unique_docs = self._remove_duplicate(split_docs, file_key)
        
        # 3. 添加标签
        final_docs = self._add_universal_tag(unique_docs)
        
        # 清理缓存
        if file_key in self.duplicate_cache:
            del self.duplicate_cache[file_key]
        
        return final_docs

    def process_documents(self, file_path: str) -> List["Document"]:
        """完整流程：加载→处理（供单独使用）"""
        raw_docs = self.load_file(file_path)
        return self.process_raw_docs(raw_docs, file_path)


__all__ = ["IngestionManager"]
