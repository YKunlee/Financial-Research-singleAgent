"""
loader.py - PDF 文档解析与切分

职责：
1. 使用 PyMuPDF4LLM 将 PDF 转换为 Markdown 格式
2. 保留金融报表的表格结构
3. 使用 MarkdownHeaderTextSplitter 按标题层级切分
4. 确保表格行的完整性

技术规格：
- chunk_size: 600
- chunk_overlap: 60
- 输出格式: Markdown
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def _log(msg: str, level: str = "INFO") -> None:
    """统一日志输出格式"""
    print(f"[PDFLoader][{level}] {msg}")


class PDFLoader:
    """
    PDF 文档加载器
    
    将 PDF 文件转换为可索引的文本块，保留文档结构。
    
    使用示例：
        loader = PDFLoader()
        chunks = loader.load_and_split("report.pdf")
    """
    
    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 60
    ):
        """
        初始化 PDF 加载器
        
        Args:
            chunk_size: 每个文本块的最大字符数
            chunk_overlap: 相邻文本块的重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Markdown 标题分割器 - 按标题层级切分
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4"),
            ],
            strip_headers=False  # 保留标题在内容中
        )
        
        # 递归字符分割器 - 用于二次切分过长的块
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""],
            keep_separator=True
        )
    
    def pdf_to_markdown(self, pdf_path: str) -> str:
        """
        将 PDF 文件转换为 Markdown 格式
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            Markdown 格式的文本内容
        """
        import pymupdf
        
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
        
        if not path.suffix.lower() == ".pdf":
            raise ValueError(f"文件格式不正确，期望 .pdf，实际: {path.suffix}")
        
        # 获取文件大小
        file_size_kb = path.stat().st_size / 1024
        _log(f"开始转换PDF: {path.name} (大小: {file_size_kb:.2f} KB)")
        
        start_time = time.time()
        
        # 先尝试 PyMuPDF4LLM（对结构化文档效果好）
        markdown_content = pymupdf4llm.to_markdown(str(path))
        
        # 如果 pymupdf4llm 提取内容过少，回退到原生文本提取
        # 这能处理 pymupdf4llm 无法正确解析的特殊布局PDF
        if len(markdown_content.strip()) < 50:
            _log("pymupdf4llm 提取内容过少，回退到原生文本提取", "WARN")
            doc = pymupdf.open(str(path))
            text_parts = []
            for page_num, page in enumerate(doc):
                page_text = page.get_text('text')
                if page_text.strip():
                    text_parts.append(f"# 第 {page_num + 1} 页\n\n{page_text}")
            doc.close()
            markdown_content = "\n\n".join(text_parts)
        
        elapsed = time.time() - start_time
        
        # 统计转换结果
        char_count = len(markdown_content)
        line_count = markdown_content.count('\n') + 1
        _log(f"PDF转换完成: 耗时 {elapsed:.2f}s, 字符数 {char_count}, 行数 {line_count}")
        
        return markdown_content
    
    def _protect_tables(self, markdown: str) -> tuple[str, Dict[str, str]]:
        """
        保护表格内容，防止被切分破坏
        
        策略：用占位符替换表格，切分后再还原
        
        Args:
            markdown: Markdown 文本
            
        Returns:
            (处理后的文本, 表格映射字典)
        """
        table_pattern = r'(\|[^\n]+\|\n)+(\|[-:\s|]+\|\n)?(\|[^\n]+\|\n)+'
        tables = {}
        
        def replace_table(match):
            table_id = f"__TABLE_{len(tables)}__"
            table_content = match.group(0)
            tables[table_id] = table_content
            # 统计表格行数
            row_count = table_content.count('\n')
            _log(f"保护表格 {table_id}: {row_count} 行, {len(table_content)} 字符", "DEBUG")
            return f"\n{table_id}\n"
        
        protected_markdown = re.sub(table_pattern, replace_table, markdown)
        _log(f"表格保护完成: 共发现 {len(tables)} 个表格")
        return protected_markdown, tables
    
    def _restore_tables(self, text: str, tables: Dict[str, str]) -> str:
        """
        还原被保护的表格
        
        Args:
            text: 包含占位符的文本
            tables: 表格映射字典
            
        Returns:
            还原表格后的文本
        """
        for table_id, table_content in tables.items():
            text = text.replace(table_id, table_content)
        return text
    
    def load_and_split(
        self,
        pdf_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        加载 PDF 并切分为文本块
        
        Args:
            pdf_path: PDF 文件路径
            metadata: 附加的元数据（如来源、上传时间等）
            
        Returns:
            文本块列表，每个块包含 content 和 metadata
        """
        total_start = time.time()
        _log(f"========== 开始处理文件: {pdf_path} ==========")
        
        # 1. PDF -> Markdown
        markdown_content = self.pdf_to_markdown(pdf_path)
        
        # 2. 保护表格
        protected_content, tables = self._protect_tables(markdown_content)
        
        # 3. 按标题层级切分
        _log("开始按标题层级切分...")
        split_start = time.time()
        header_splits = self.header_splitter.split_text(protected_content)
        split_elapsed = time.time() - split_start
        _log(f"标题切分完成: 产生 {len(header_splits)} 个初始块, 耗时 {split_elapsed:.2f}s")
        
        # 4. 二次切分过长的块
        chunks = []
        source_name = Path(pdf_path).name
        oversized_count = 0
        
        for i, doc in enumerate(header_splits):
            # 提取文本内容
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            
            # 还原表格
            content = self._restore_tables(content, tables)
            
            # 如果内容过长，进一步切分
            if len(content) > self.chunk_size:
                oversized_count += 1
                sub_chunks = self.text_splitter.split_text(content)
                _log(f"块 {i} 过长({len(content)}字符), 二次切分为 {len(sub_chunks)} 个子块", "DEBUG")
                for j, sub_chunk in enumerate(sub_chunks):
                    chunk_metadata = {
                        "source": source_name,
                        "chunk_index": f"{i}_{j}",
                        **(metadata or {})
                    }
                    # 从 header_splits 提取标题元数据
                    if hasattr(doc, 'metadata'):
                        chunk_metadata.update(doc.metadata)
                    
                    chunks.append({
                        "content": sub_chunk,
                        "metadata": chunk_metadata
                    })
            else:
                chunk_metadata = {
                    "source": source_name,
                    "chunk_index": str(i),
                    **(metadata or {})
                }
                if hasattr(doc, 'metadata'):
                    chunk_metadata.update(doc.metadata)
                
                chunks.append({
                    "content": content,
                    "metadata": chunk_metadata
                })
        
        total_elapsed = time.time() - total_start
        
        # 统计信息
        chunk_sizes = [len(c["content"]) for c in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunks else 0
        min_size = min(chunk_sizes) if chunks else 0
        max_size = max(chunk_sizes) if chunks else 0
        
        _log(f"切分统计: 总块数={len(chunks)}, 二次切分={oversized_count}个")
        _log(f"块大小: 平均={avg_size:.0f}, 最小={min_size}, 最大={max_size}")
        _log(f"========== 处理完成: {source_name}, 总耗时 {total_elapsed:.2f}s ==========")
        
        return chunks
    
    def load_directory(
        self,
        directory_path: str,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        加载目录下的所有 PDF 文件
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归子目录
            
        Returns:
            所有文档的文本块列表
        """
        dir_path = Path(directory_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(dir_path.glob(pattern))
        
        _log(f"扫描目录: {directory_path}, 递归={recursive}, 发现 {len(pdf_files)} 个PDF文件")
        
        all_chunks = []
        success_count = 0
        fail_count = 0
        
        for idx, pdf_file in enumerate(pdf_files, 1):
            _log(f"进度: [{idx}/{len(pdf_files)}] 处理 {pdf_file.name}")
            try:
                chunks = self.load_and_split(str(pdf_file))
                all_chunks.extend(chunks)
                success_count += 1
            except Exception as e:
                fail_count += 1
                _log(f"处理失败: {pdf_file} - {e}", "ERROR")
        
        _log(f"目录加载完成: 成功={success_count}, 失败={fail_count}, 总块数={len(all_chunks)}")
        return all_chunks
