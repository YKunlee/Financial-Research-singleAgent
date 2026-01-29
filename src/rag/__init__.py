"""
RAG 模块 - 检索增强生成

包含：
- loader: PDF 文档解析与切分
- vectorstore: ChromaDB 向量存储管理
- ingest: 文档索引脚本（写操作）

读写分离架构：
- ingest.py: 负责"写"操作（索引构建），独立运行
- vectorstore.py: 负责"读"操作（向量检索），应用内使用
"""

from .loader import PDFLoader
from .vectorstore import VectorStore
from .ingest import ingest_documents

__all__ = ["PDFLoader", "VectorStore", "ingest_documents"]
