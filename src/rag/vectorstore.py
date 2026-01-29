"""
vectorstore.py - ChromaDB 向量存储管理

职责：
1. 使用 PersistentClient 持久化存储向量数据
2. 使用 BAAI/bge-small-zh-v1.5 嵌入模型（适配CPU）
3. 提供增删改查接口
4. 实现相似度阈值过滤

技术规格：
- 存储路径: ./data/chroma_db
- 嵌入模型: BAAI/bge-small-zh-v1.5
- 相似度阈值: 0.35
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


def _log(msg: str, level: str = "INFO") -> None:
    """统一日志输出格式"""
    print(f"[VectorStore][{level}] {msg}")


class VectorStore:
    """
    向量存储管理器
    
    基于 ChromaDB 的本地持久化向量数据库，
    使用 bge-small-zh-v1.5 作为中文嵌入模型。
    
    使用示例：
        store = VectorStore()
        store.add_documents(chunks)
        results = store.search("公司财务状况")
    """
    
    # 默认配置
    DEFAULT_DB_PATH = "./data/chroma_db"
    DEFAULT_COLLECTION_NAME = "financial_docs"
    DEFAULT_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
    # 相似度阈值：只有相关度高于这个值的文档才会被返回
    # 设成 0.6 可以过滤掉那些"沾点边但不太相关"的结果，比如只是碰巧包含相同数字的文档
    DEFAULT_THRESHOLD = 0.7
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        model_name: Optional[str] = None,
        threshold: float = DEFAULT_THRESHOLD
    ):
        """
        初始化向量存储
        
        Args:
            db_path: ChromaDB 持久化路径，默认 ./data/chroma_db
            collection_name: 集合名称，默认 financial_docs
            model_name: 嵌入模型名称，默认 BAAI/bge-small-zh-v1.5
            threshold: 相似度阈值，默认 0.35
        """
        _log("========== 初始化向量存储 ==========")
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.collection_name = collection_name or self.DEFAULT_COLLECTION_NAME
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.threshold = threshold
        
        _log(f"配置: db_path={self.db_path}, collection={self.collection_name}")
        _log(f"配置: model={self.model_name}, threshold={self.threshold}")
        
        # 确保数据目录存在
        Path(self.db_path).mkdir(parents=True, exist_ok=True)
        
        # 初始化嵌入模型
        _log(f"加载嵌入模型: {self.model_name}...")
        model_start = time.time()
        self._embedding_model = SentenceTransformer(self.model_name)
        model_elapsed = time.time() - model_start
        _log(f"嵌入模型加载完成, 耗时 {model_elapsed:.2f}s")
        
        # 初始化 ChromaDB 客户端
        _log(f"连接数据库: {self.db_path}")
        self._client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 获取或创建集合
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
        
        doc_count = self._collection.count()
        _log(f"集合 '{self.collection_name}' 已就绪, 当前文档数: {doc_count}")
        _log("========== 初始化完成 ==========")
    
    def _generate_id(self, content: str, source: str) -> str:
        """
        生成文档的唯一ID
        
        Args:
            content: 文档内容
            source: 来源文件名
            
        Returns:
            唯一ID字符串
        """
        hash_input = f"{source}:{content[:100]}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本嵌入向量
        
        Args:
            texts: 待嵌入的文本列表
            
        Returns:
            嵌入向量列表
        """
        start_time = time.time()
        embeddings = self._embedding_model.encode(texts, normalize_embeddings=True)
        elapsed = time.time() - start_time
        
        # 获取嵌入维度
        dim = len(embeddings[0]) if len(embeddings) > 0 else 0
        _log(f"嵌入生成: {len(texts)}条文本, 维度={dim}, 耗时 {elapsed:.3f}s", "DEBUG")
        
        return embeddings.tolist()
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        添加文档到向量库（增量索引）
        
        Args:
            documents: 文档列表，每个文档包含 content 和 metadata
            batch_size: 批量处理大小
            
        Returns:
            成功添加的文档数量
        """
        if not documents:
            _log("无文档需要添加")
            return 0
        
        _log(f"========== 开始添加文档: 共 {len(documents)} 个 ==========")
        total_start = time.time()
        added_count = 0
        skipped_count = 0
        batch_count = (len(documents) + batch_size - 1) // batch_size
        
        # 分批处理
        for batch_idx, i in enumerate(range(0, len(documents), batch_size), 1):
            batch = documents[i:i + batch_size]
            _log(f"处理批次 [{batch_idx}/{batch_count}], 本批 {len(batch)} 个文档")
            
            ids = []
            texts = []
            metadatas = []
            
            for doc in batch:
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
                source = metadata.get("source", "unknown")
                
                if not content.strip():
                    skipped_count += 1
                    continue
                
                doc_id = self._generate_id(content, source)
                ids.append(doc_id)
                texts.append(content)
                metadatas.append(metadata)
            
            if not texts:
                _log(f"批次 {batch_idx} 无有效文档, 跳过", "DEBUG")
                continue
            
            # 生成嵌入向量
            embeddings = self._embed(texts)
            
            # 添加到集合（upsert 模式，存在则更新）
            upsert_start = time.time()
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            upsert_elapsed = time.time() - upsert_start
            _log(f"批次 {batch_idx} 写入完成, 耗时 {upsert_elapsed:.3f}s", "DEBUG")
            
            added_count += len(texts)
        
        total_elapsed = time.time() - total_start
        _log(f"添加完成: 成功={added_count}, 跳过={skipped_count}, 总耗时 {total_elapsed:.2f}s")
        _log(f"当前库中文档总数: {self._collection.count()}")
        _log("========== 添加文档完成 ==========")
        return added_count
    
    def search(
        self,
        query: str,
        k: int = 3,
        threshold: Optional[float] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        语义检索文档
        
        Args:
            query: 查询文本
            k: 返回的最大结果数
            threshold: 相似度阈值，低于该值的结果会被过滤
            filter_metadata: 元数据过滤条件
            
        Returns:
            检索结果列表，每个结果包含 content、metadata、score
        """
        _log(f"========== 开始检索 ==========")
        _log(f"查询: '{query[:50]}{'...' if len(query) > 50 else ''}'")
        _log(f"参数: k={k}, threshold={threshold or self.threshold}, filter={filter_metadata}")
        
        if self._collection.count() == 0:
            _log("向量库为空，无法检索", "WARN")
            return []
        
        threshold = threshold if threshold is not None else self.threshold
        
        # 生成查询向量
        query_embedding = self._embed([query])[0]
        
        # 执行检索
        search_start = time.time()
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"]
        )
        search_elapsed = time.time() - search_start
        _log(f"ChromaDB查询耗时: {search_elapsed:.3f}s")
        
        # 处理结果
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        _log(f"原始结果: 返回 {len(documents)} 个文档")
        
        # 打印距离分布
        if distances:
            _log(f"距离分布: min={min(distances):.4f}, max={max(distances):.4f}, avg={sum(distances)/len(distances):.4f}", "DEBUG")
        
        # 转换距离为相似度分数（余弦距离 -> 相似度）
        # ChromaDB 使用余弦距离，范围 [0, 2]，越小越相似
        # 转换公式: similarity = 1 - distance/2
        filtered_results = []
        for idx, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            similarity = 1 - dist / 2
            source = meta.get("source", "unknown") if meta else "unknown"
            _log(f"  [{idx+1}] 距离={dist:.4f}, 相似度={similarity:.4f}, 来源={source}", "DEBUG")
            
            if similarity >= threshold:
                filtered_results.append({
                    "content": doc,
                    "metadata": meta,
                    "score": round(similarity, 4)
                })
        
        # 按相似度降序排序
        filtered_results.sort(key=lambda x: x["score"], reverse=True)
        
        _log(f"过滤后结果: {len(filtered_results)} 个 (阈值={threshold})")
        
        # 打印最终结果摘要
        for idx, r in enumerate(filtered_results):
            content_preview = r["content"][:60].replace('\n', ' ')
            _log(f"  结果[{idx+1}]: score={r['score']}, 内容='{content_preview}...'", "DEBUG")
        
        _log("========== 检索完成 ==========")
        return filtered_results
    
    def delete_by_source(self, source: str) -> int:
        """
        按来源删除文档
        
        Args:
            source: 来源文件名
            
        Returns:
            删除的文档数量
        """
        _log(f"删除来源: '{source}'")
        
        # 查询所有匹配的文档
        results = self._collection.get(
            where={"source": source},
            include=["metadatas"]
        )
        
        ids = results.get("ids", [])
        if not ids:
            _log(f"未找到来源为 '{source}' 的文档")
            return 0
        
        # 删除文档
        self._collection.delete(ids=ids)
        _log(f"已删除 {len(ids)} 个来自 '{source}' 的文档")
        _log(f"当前库中文档总数: {self._collection.count()}")
        return len(ids)
    
    def get_all_sources(self) -> List[str]:
        """
        获取所有已索引文档的来源列表
        
        Returns:
            来源文件名列表（去重）
        """
        if self._collection.count() == 0:
            return []
        
        # 获取所有元数据
        results = self._collection.get(include=["metadatas"])
        metadatas = results.get("metadatas", [])
        
        # 提取并去重来源
        sources = set()
        for meta in metadatas:
            if meta and "source" in meta:
                sources.add(meta["source"])
        
        return sorted(list(sources))
    
    def get_document_count(self) -> int:
        """
        获取当前文档总数
        
        Returns:
            文档数量
        """
        return self._collection.count()
    
    def clear_all(self) -> None:
        """
        清空所有文档（谨慎使用）
        """
        old_count = self._collection.count()
        _log(f"清空向量库: 当前有 {old_count} 个文档", "WARN")
        
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        _log("向量库已清空")
    
    def is_initialized(self) -> bool:
        """
        检查向量库是否已初始化且包含数据
        
        Returns:
            True 如果向量库存在且有数据
        """
        db_path = Path(self.db_path)
        return db_path.exists() and self._collection.count() > 0


# 全局单例（可选）
_global_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    获取全局向量存储实例（单例模式）
    
    Returns:
        VectorStore 实例
    """
    global _global_store
    if _global_store is None:
        _global_store = VectorStore()
    return _global_store
