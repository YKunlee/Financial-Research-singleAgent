"""
Chainlit 集成入口 - 金融研究 Agent

职责：
1. 接收用户消息
2. 调用 LangGraph 工作流
3. 实时流式展示处理进度
4. 格式化输出最终结果
"""

import chainlit as cl
from pathlib import Path
import sys

# 确保可以导入 src 模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.graph import app as graph_app
from src.state import make_initial_state


@cl.on_chat_start
async def on_chat_start():
    """
    会话开始时的欢迎消息
    """
    await cl.Message(
        content="👋 你好！我是金融研究助手。\n\n你可以：\n- 询问公司的财务数据（如：腾讯的市值是多少？）\n- 查询上市信息（如：小米什么时候上市的？）\n- 日常对话（如：你好）\n\n请直接输入公司名或问题即可开始。"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    处理用户消息的主函数
    
    流程：
    1. 接收用户输入
    2. 初始化 State
    3. 调用 LangGraph 执行流程
    4. 实时展示各节点处理状态
    5. 返回最终结果
    """
    user_query = message.content.strip()
    
    if not user_query:
        await cl.Message(content="请输入有效的查询内容。").send()
        return
    
    # 显示处理中的消息
    processing_msg = cl.Message(content="")
    await processing_msg.send()
    
    try:
        # 初始化状态
        initial_state = make_initial_state(user_query)
        
        # 调试日志：打印初始状态关键信息
        print('\n' + '=' * 80)
        print('[DEBUG] 收到用户查询:', user_query)
        print('[DEBUG] 初始状态:', {k: initial_state.get(k) for k in ['user_query', 'company_name', 'intent', 'need_financial', 'need_listing']})
        print('=' * 80)
        
        # 执行 LangGraph 工作流（流式处理）
        result_state = {}
        step_count = 0
        
        async for event in graph_app.astream(initial_state, stream_mode="updates"):
            step_count += 1
            
            # 提取节点名称和状态更新
            for node_name, node_output in event.items():
                # 更新处理进度
                trace = node_output.get("trace", [])
                if trace:
                    latest_trace = trace[-1] if isinstance(trace, list) else str(trace)
                    await processing_msg.stream_token(f"✓ {node_name}: {latest_trace}\n")
                
                # 调试日志：打印每个节点的关键输出
                if isinstance(node_output, dict):
                    debug_keys = ['company_name', 'intent', 'need_financial', 'need_listing', 'financial_data', 'listing_data', 'card_json', 'errors']
                    print('[DEBUG] step =', step_count, 'node =', node_name)
                    print('[DEBUG] 节点输出片段:', {k: node_output.get(k) for k in debug_keys if k in node_output})
                
                    # 合并当前节点的状态更新到总状态中
                    # 对于列表类字段（如 errors / trace），LangGraph 已在内部负责合并
                    # 这里简单覆盖即可，保留其他节点写入的字段
                    result_state.update(node_output)
        
        # 调试日志：打印最终聚合状态
        print('[DEBUG] 最终 result_state 关键信息:', {k: result_state.get(k) for k in ['company_name', 'intent', 'need_financial', 'need_listing', 'financial_data', 'listing_data', 'card_json', 'errors']})
        print('=' * 80 + '\n')
        
        # 结束处理状态消息
        await processing_msg.update()
        
        # 提取最终结果
        if result_state is None:
            await cl.Message(content="❌ 处理失败：工作流未返回结果").send()
            return
        
        # 根据 intent 类型生成不同的输出
        intent = result_state.get("intent", "chat")
        card_json = result_state.get("card_json", {})
        errors = result_state.get("errors", [])
        
        if intent == "chat":
            # 对话模式：直接返回文本
            chat_reply = result_state.get("chat_reply", "抱歉，我无法理解你的问题。")
            await cl.Message(content=chat_reply).send()
        
        else:
            # 金融查询模式：格式化展示卡片数据
            company_name = result_state.get("company_name", "未知公司")
            
            # 构建富文本输出
            output_lines = [f"## 📊 {company_name} 的研究报告\n"]
            
            sections = card_json.get("sections", [])
            if sections:
                for section in sections:
                    section_title = section.get("title", "数据")
                    items = section.get("items", [])
                    source = section.get("source", "未知")
                    
                    output_lines.append(f"### {section_title}")
                    for item in items:
                        label = item.get("label", "")
                        value = item.get("value", "")
                        output_lines.append(f"- **{label}**: {value}")
                    output_lines.append(f"\n*数据来源: {source}*\n")
            else:
                output_lines.append("暂无数据")
            
            # 显示警告信息
            if errors:
                output_lines.append("\n⚠️ **警告**:")
                for error in errors:
                    output_lines.append(f"- {error}")
            
            # 发送格式化后的结果
            await cl.Message(content="\n".join(output_lines)).send()
    
    except Exception as e:
        # 错误处理
        error_msg = f"❌ 处理过程中发生错误：\n```\n{str(e)}\n```"
        await cl.Message(content=error_msg).send()


if __name__ == "__main__":
    # Chainlit 会通过命令行启动，不需要手动运行
    pass
