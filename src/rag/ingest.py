"""
ingest.py - 文档索引脚本（写操作）

职责：
1. 扫描 PDF 目录
2. 使用 PDFLoader 加载并切分文档
3. 使用 VectorStore.add_documents 写入向量库
4. 显式调用 persist() 确保持久化

使用方式：
    python -m src.rag.ingest           # 增量索引（只处理新文件）
    python -m src.rag.ingest --force   # 强制重建索引

读写分离设计：
- 本模块负责所有"写"操作（索引构建）
- app.py 只负责"读"操作（向量检索）
- 避免应用启动时执行索引，防止锁库
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Set

from .loader import PDFLoader
from .vectorstore import VectorStore


# ==================== 配置 ====================
PDF_DIR = Path("./data/pdfs")
DB_PATH = "./data/chroma_db"


def _log(msg: str, level: str = "INFO") -> None:
    """统一日志输出格式"""
    print(f"[Ingest][{level}] {msg}")


def get_indexed_sources(store: VectorStore) -> Set[str]:
    """
    获取已索引的文件来源列表
    
    Args:
        store: VectorStore 实例
        
    Returns:
        已索引的文件名集合
    """
    return set(store.get_all_sources())


def scan_pdf_directory(pdf_dir: Path) -> List[Path]:
    """
    扫描 PDF 目录，获取所有 PDF 文件
    
    Args:
        pdf_dir: PDF 文件目录
        
    Returns:
        PDF 文件路径列表
    """
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = list(pdf_dir.glob("*.pdf"))
    _log(f"扫描目录: {pdf_dir}, 发现 {len(pdf_files)} 个 PDF 文件")
    return pdf_files


def ingest_documents(
    pdf_dir: Path = PDF_DIR,
    force: bool = False
) -> int:
    """
    执行文档索引（主入口函数）
    
    Args:
        pdf_dir: PDF 文件目录
        force: 是否强制重建索引（忽略已索引文件）
        
    Returns:
        本次索引的文档片段数量
    """
    total_start = time.time()
    
    _log("=" * 60)
    _log("开始文档索引任务")
    _log(f"PDF 目录: {pdf_dir}")
    _log(f"强制模式: {force}")
    _log("=" * 60)
    
    # 1. 扫描 PDF 目录
    pdf_files = scan_pdf_directory(pdf_dir)
    if not pdf_files:
        _log("PDF 目录为空，无文件需要索引")
        return 0
    
    # 2. 初始化组件
    _log("初始化 VectorStore...")
    store = VectorStore(db_path=DB_PATH)
    
    _log("初始化 PDFLoader...")
    loader = PDFLoader()
    
    # 3. 确定需要索引的文件
    if force:
        # 强制模式：清空现有数据，重新索引全部
        _log("强制模式：清空现有索引...")
        store.clear_all()
        files_to_index = pdf_files
    else:
        # 增量模式：只索引新文件
        indexed_sources = get_indexed_sources(store)
        files_to_index = [
            f for f in pdf_files 
            if f.name not in indexed_sources
        ]
        _log(f"增量模式：已索引 {len(indexed_sources)} 个文件，待索引 {len(files_to_index)} 个新文件")
    
    if not files_to_index:
        _log("所有文件已索引，无需重复处理")
        _log("索引已更新")
        return 0
    
    # 4. 逐个处理 PDF 文件
    total_chunks = 0
    success_count = 0
    fail_count = 0
    
    for idx, pdf_path in enumerate(files_to_index, 1):
        _log(f"[{idx}/{len(files_to_index)}] 处理: {pdf_path.name}")
        
        try:
            # 加载并切分文档
            chunks = loader.load_and_split(str(pdf_path))
            
            if chunks:
                # 写入向量库
                added = store.add_documents(chunks)
                total_chunks += added
                success_count += 1
                _log(f"✓ {pdf_path.name} 已索引 {added} 个片段")
            else:
                _log(f"⚠ {pdf_path.name} 无有效内容")
                
        except Exception as e:
            fail_count += 1
            _log(f"✗ {pdf_path.name} 索引失败: {e}", "ERROR")
    
    # 5. 完成统计
    total_elapsed = time.time() - total_start
    
    _log("=" * 60)
    _log("索引任务完成")
    _log(f"成功: {success_count}, 失败: {fail_count}")
    _log(f"新增片段: {total_chunks}")
    _log(f"总耗时: {total_elapsed:.2f}s")
    _log(f"当前库中文档总数: {store.get_document_count()}")
    _log("=" * 60)
    
    # 打印完成标识
    print("\n" + "=" * 60)
    print("索引已更新")
    print("=" * 60 + "\n")
    
    return total_chunks


def main():
    """
    命令行入口
    
    用法：
        python -m src.rag.ingest           # 增量索引
        python -m src.rag.ingest --force   # 强制重建
        python -m src.rag.ingest --dir ./my_pdfs  # 指定目录
    """
    parser = argparse.ArgumentParser(
        description="RAG 文档索引工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    python -m src.rag.ingest              # 增量索引（推荐）
    python -m src.rag.ingest --force      # 强制重建全部索引
    python -m src.rag.ingest --dir ./docs # 指定 PDF 目录
        """
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制重建索引（清空现有数据后重新索引全部）"
    )
    
    parser.add_argument(
        "--dir", "-d",
        type=str,
        default=str(PDF_DIR),
        help=f"PDF 文件目录，默认: {PDF_DIR}"
    )
    
    args = parser.parse_args()
    
    pdf_dir = Path(args.dir)
    
    try:
        ingest_documents(pdf_dir=pdf_dir, force=args.force)
        sys.exit(0)
    except Exception as e:
        _log(f"索引任务异常终止: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
