"""
retriever.py - RAG 检索节点

职责：
1. 从 State 提取用户查询
2. 调用 VectorStore 执行语义检索
3. 将检索结果注入 State.context
4. 使用 cl.Step 包裹以防界面假死

技术规格：
- 检索数量: 3
- 相似度阈值: 0.7
- 异步执行，CPU友好
"""

from __future__ import annotations

import time
from typing import Dict, Any, List
import asyncio

# Chainlit 导入（可选，用于Step包裹）
try:
    import chainlit as cl
    HAS_CHAINLIT = True
except ImportError:
    HAS_CHAINLIT = False


def _log(msg: str, level: str = "INFO") -> None:
    """统一日志输出格式"""
    print(f"[RetrieverNode][{level}] {msg}")


def _sync_retrieve(user_query: str) -> List[str]:
    """
    同步检索函数（在线程池中执行）
    
    Args:
        user_query: 用户查询
        
    Returns:
        检索到的文档内容列表
    """
    # 延迟导入，避免循环依赖和启动时加载
    from src.rag.vectorstore import get_vector_store
    
    _log(f"同步检索开始: '{user_query[:50]}{'...' if len(user_query) > 50 else ''}'")
    start_time = time.time()
    
    try:
        store = get_vector_store()
        
        # 检查向量库是否有数据
        doc_count = store.get_document_count()
        _log(f"向量库文档数: {doc_count}")
        
        if doc_count == 0:
            _log("向量库为空，跳过检索", "WARN")
            return []
        
        # 执行检索，阈值使用 VectorStore 的默认配置
        results = store.search(
            query=user_query,
            k=3
        )
        
        # 提取文档内容
        context_list = []
        for idx, result in enumerate(results):
            content = result.get("content", "")
            source = result.get("metadata", {}).get("source", "未知来源")
            score = result.get("score", 0)
            
            # 格式化上下文：包含来源信息
            formatted = f"[来源: {source}, 相关度: {score}]\n{content}"
            context_list.append(formatted)
            
            # 输出每条结果摘要
            content_preview = content[:80].replace('\n', ' ')
            _log(f"  结果[{idx+1}]: score={score}, 来源={source}", "DEBUG")
            _log(f"    内容: {content_preview}...", "DEBUG")
        
        elapsed = time.time() - start_time
        _log(f"同步检索完成: 返回 {len(context_list)} 条, 耗时 {elapsed:.3f}s")
        return context_list
        
    except Exception as e:
        elapsed = time.time() - start_time
        _log(f"检索出错: {e}, 耗时 {elapsed:.3f}s", "ERROR")
        return []


async def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    RAG 检索节点
    
    从向量库中检索与用户查询相关的文档片段，
    并将结果注入到 State.context 中供后续节点使用。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        状态更新字典，包含 context 和 trace
    """
    _log("========== 检索节点开始 ==========")
    total_start = time.time()
    
    user_query = state.get("user_query", "")
    session_id = state.get("session_id", "unknown")
    
    _log(f"会话ID: {session_id}")
    _log(f"用户查询: '{user_query[:80]}{'...' if len(user_query) > 80 else ''}'")
    
    if not user_query.strip():
        _log("查询为空，跳过检索", "WARN")
        return {
            "context": [],
            "trace": ["retrieve_node: 查询为空，跳过检索"]
        }
    
    # 使用 Chainlit Step 包裹（防止界面假死）
    if HAS_CHAINLIT:
        _log("使用 Chainlit Step 模式")
        try:
            async with cl.Step(name="RAG检索", type="retrieval") as step:
                step.input = user_query
                
                # 在线程池中执行同步检索（避免阻塞事件循环）
                loop = asyncio.get_event_loop()
                context_list = await loop.run_in_executor(
                    None,
                    _sync_retrieve,
                    user_query
                )
                
                step.output = f"检索到 {len(context_list)} 个相关文档片段"
        except Exception as e:
            _log(f"Chainlit Step 执行出错: {e}, 降级为普通执行", "ERROR")
            # 降级为普通执行
            loop = asyncio.get_event_loop()
            context_list = await loop.run_in_executor(
                None,
                _sync_retrieve,
                user_query
            )
    else:
        _log("无 Chainlit 环境，使用普通模式")
        # 无 Chainlit 环境，直接执行
        loop = asyncio.get_event_loop()
        context_list = await loop.run_in_executor(
            None,
            _sync_retrieve,
            user_query
        )
    
    # 生成追踪信息
    if context_list:
        trace_msg = f"retrieve_node: 检索到 {len(context_list)} 个相关文档"
        # 统计上下文总长度
        total_context_len = sum(len(c) for c in context_list)
        _log(f"上下文统计: {len(context_list)} 条, 总长度 {total_context_len} 字符")
    else:
        trace_msg = "retrieve_node: 未找到相关文档"
        _log("未检索到相关文档", "WARN")
    
    total_elapsed = time.time() - total_start
    _log(f"节点总耗时: {total_elapsed:.3f}s")
    _log("========== 检索节点完成 ==========")
    
    return {
        "context": context_list,
        "trace": [trace_msg]
    }


# 同步版本（用于测试或非异步环境）
def retrieve_node_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    检索节点的同步版本
    
    Args:
        state: 当前工作流状态
        
    Returns:
        状态更新字典
    """
    _log("========== 同步检索节点开始 ==========")
    total_start = time.time()
    
    user_query = state.get("user_query", "")
    
    if not user_query.strip():
        _log("查询为空，跳过检索", "WARN")
        return {
            "context": [],
            "trace": ["retrieve_node: 查询为空，跳过检索"]
        }
    
    context_list = _sync_retrieve(user_query)
    
    if context_list:
        trace_msg = f"retrieve_node: 检索到 {len(context_list)} 个相关文档"
        total_context_len = sum(len(c) for c in context_list)
        _log(f"上下文统计: {len(context_list)} 条, 总长度 {total_context_len} 字符")
    else:
        trace_msg = "retrieve_node: 未找到相关文档"
        _log("未检索到相关文档", "WARN")
    
    total_elapsed = time.time() - total_start
    _log(f"节点总耗时: {total_elapsed:.3f}s")
    _log("========== 同步检索节点完成 ==========")
    
    return {
        "context": context_list,
        "trace": [trace_msg]
    }
