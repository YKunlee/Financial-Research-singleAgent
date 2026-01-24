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
from datetime import datetime

# 确保可以导入 src 模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.graph import app as graph_app
from src.state import make_initial_state
from src.data_layer import SQLiteDataLayer  # 使用 SQLite 持久化存储


# ==================== 数据层初始化 ====================
# 创建SQLite数据层实例，对话历史持久化存储到数据库
# 数据库文件位置：项目根目录下的 chainlit_data.db
data_layer = SQLiteDataLayer(db_path="chainlit_data.db")


@cl.data_layer
def get_data_layer():
    """
    返回数据层实例
    
    Chainlit 会调用这个函数来获取数据层，
    用于管理会话历史和消息存储
    """
    return data_layer


# ==================== 认证配置 ====================
# Chainlit 需要认证才能显示侧边栏的会话历史
# 这里使用简单的密码认证，适合开发测试

@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """
    密码认证回调
    
    白话解释：
    就像登录微信一样，输入用户名密码后才能看到自己的聊天记录
    
    测试账号：
    - 用户名: admin
    - 密码: admin
    
    也可以直接输入任意用户名，密码留空（方便测试）
    """
    user_obj = None
    
    # 方式1：管理员账号
    if username == "admin" and password == "admin":
        user_obj = cl.User(
            identifier="admin",
            metadata={"role": "admin", "provider": "credentials"}
        )
    # 方式2：任意用户名，无需密码（方便快速测试）
    # 只要输入用户名就能登录，密码可以为空
    elif username and len(username) > 0:
        user_obj = cl.User(
            identifier=username,
            metadata={"role": "user", "provider": "credentials"}
        )
    
    # 如果认证成功，将用户保存到数据层
    if user_obj:
        print(f"[auth_callback] 认证成功，用户: {user_obj.identifier}")
        # 创建用户记录
        await data_layer.create_user(user_obj)
        return user_obj
    
    # 认证失败
    print(f"[auth_callback] 认证失败，用户名: {username}")
    return None


@cl.on_chat_start
async def on_chat_start():
    """
    新会话开始时的欢迎消息
    
    场景：用户点击"新建对话"或刷新页面时触发
    
    白话解释：
    Chainlit 每次刷新都会生成新的 thread_id（这是框架设计）
    我们的策略：
    1. 先清理该用户的空会话（拿了号但没点单的）
    2. 再创建新会话（因为 Chainlit 已经给了新号码牌）
    """
    # 初始化会话历史存储
    cl.user_session.set("history", [])
    
    # ==================== 获取会话信息 ====================
    thread_id = cl.context.session.thread_id
    user = cl.context.session.user
    user_id = user.identifier if user else "anonymous"
    
    print(f"\n{'='*60}")
    print(f"[on_chat_start] 触发会话启动")
    print(f"[on_chat_start] thread_id={thread_id}")
    print(f"[on_chat_start] user_id={user_id}")
    
    # ==================== 清理该用户的空会话/无效会话 ====================
    # 白话：把这个用户之前"拿了号但没好好点单"的废账单删掉
    # 策略：删除消息数 <= 2 的会话（可能只有欢迎消息，或只有1轮简单测试对话）
    conn = data_layer._get_connection()
    cursor = conn.cursor()
    
    # 查找该用户的所有低价值会话（消息数 <= 2）
    cursor.execute("""
        SELECT t.id, t.name, COUNT(s.id) as msg_count
        FROM threads t
        LEFT JOIN steps s ON t.id = s.thread_id
        WHERE t.user_id = ?
        GROUP BY t.id
        HAVING msg_count <= 2
    """, (user_id,))
    
    low_value_threads = cursor.fetchall()
    if low_value_threads:
        print(f"[on_chat_start] 发现 {len(low_value_threads)} 个无效会话（消息数≤2），开始清理...")
        for thread_item in low_value_threads:
            # 删除会话及其消息
            cursor.execute("DELETE FROM threads WHERE id = ?", (thread_item['id'],))
            cursor.execute("DELETE FROM steps WHERE thread_id = ?", (thread_item['id'],))
            print(f"  ✓ 删除会话: {thread_item['name']} (消息数: {thread_item['msg_count']})")
        conn.commit()
        print(f"[on_chat_start] ✓ 已清理 {len(low_value_threads)} 个无效会话")
    
    conn.close()
    
    # ==================== 创建新会话 ====================
    # 由于 Chainlit 已经分配了新的 thread_id，直接创建即可
    print(f"[on_chat_start] 创建新会话...")
    await data_layer.create_thread({
        "id": thread_id,
        "name": "New Chat",
        "userId": user_id,
        "createdAt": None,
        "metadata": {},
        "tags": []
    })
    print(f"[on_chat_start] ✓ 新会话创建成功")
    print(f"{'='*60}\n")
    
    # 发送欢迎消息
    await cl.Message(
        content="👋 你好！我是金融研究助手。\n\n你可以：\n- 询问公司的财务数据（如：腾讯的市值是多少？）\n- 查询上市信息（如：小米什么时候上市的？）\n- 日常对话（如：你好）\n\n请直接输入公司名或问题即可开始。"
    ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: dict):
    """
    恢复旧会话时的处理
    
    场景：用户从侧边栏点击某个历史会话时触发
    
    功能：
    1. 加载该会话的历史消息
    2. 重新构建会话上下文
    3. 展示欢迎消息
    
    白话解释：
    就像翻开一本旧笔记本，把之前写的内容重新加载进来
    """
    thread_id = thread.get("id")
    thread_name = thread.get("name", "未命名会话")
    
    # [DEBUG] print(f"\n{'='*60}")
    # [DEBUG] print(f"[on_chat_resume] === 恢复会话详细日志 ===")
    # [DEBUG] print(f"[on_chat_resume] thread_id: {thread_id}")
    # [DEBUG] print(f"[on_chat_resume] thread_name: {thread_name}")
    
    # 检查 thread 对象中是否已包含 steps
    thread_steps = thread.get("steps", [])
    # [DEBUG] print(f"[on_chat_resume] thread 对象中的 steps 数量: {len(thread_steps)}")
    # [DEBUG] if thread_steps:
    # [DEBUG]     print(f"[on_chat_resume] thread.steps 详情:")
    # [DEBUG]     for i, step in enumerate(thread_steps):
    # [DEBUG]         step_type = step.get("type", "")
    # [DEBUG]         step_name = step.get("name", "")
    # [DEBUG]         step_output = step.get("output", "")[:50] + "..." if len(step.get("output", "")) > 50 else step.get("output", "")
    # [DEBUG]         print(f"[on_chat_resume]   [{i}] type={step_type}, name={step_name}, output={step_output}")
    
    # 从数据层获取历史消息
    history_steps = data_layer.get_thread_messages(thread_id)
    # [DEBUG] print(f"[on_chat_resume] data_layer.get_thread_messages 返回 {len(history_steps)} 条")
    
    # 重建会话历史（转换为标准格式）
    history = []
    for step in history_steps:
        step_type = step.get("type", "")
        step_name = step.get("name", "")
        step_output = step.get("output", "")
        
        # 只提取用户消息和助手回复
        if step_type == "user_message":
            history.append({"role": "user", "content": step_output})
            # [DEBUG] print(f"[on_chat_resume]   添加 user 消息: {step_output[:30]}...")
        elif step_type == "assistant_message" or step_name == "assistant":
            history.append({"role": "assistant", "content": step_output})
            # [DEBUG] print(f"[on_chat_resume]   添加 assistant 消息: {step_output[:30]}...")
        # [DEBUG] else:
        # [DEBUG]     print(f"[on_chat_resume]   跳过消息: type={step_type}, name={step_name}")
    
    # 保存到当前会话
    cl.user_session.set("history", history)
    
    # [DEBUG] print(f"[on_chat_resume] 最终 history 列表包含 {len(history)} 条消息")
    # [DEBUG] print(f"{'='*60}\n")


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
        # 获取会话历史（最近5轮=10条消息）
        history = cl.user_session.get("history", [])
        recent_history = history[-10:] if len(history) > 10 else history
        
        # 初始化状态
        initial_state = make_initial_state(user_query)
        # 传入历史上下文到 State
        initial_state["conversation_history"] = recent_history
        
        # 调试日志：打印初始状态关键信息
        # [DEBUG] print('\n' + '=' * 80)
        # [DEBUG] print('[DEBUG] 收到用户查询:', user_query)
        # [DEBUG] print('[DEBUG] 初始状态:', {k: initial_state.get(k) for k in ['user_query', 'company_name', 'intent', 'need_financial', 'need_listing']})
        # [DEBUG] print('[DEBUG] 会话历史长度:', len(recent_history))
        # [DEBUG] print('=' * 80)
        
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
                    # [DEBUG] debug_keys = ['company_name', 'intent', 'need_financial', 'need_listing', 'financial_data', 'listing_data', 'card_json', 'errors']
                    # [DEBUG] print('[DEBUG] step =', step_count, 'node =', node_name)
                    # [DEBUG] print('[DEBUG] 节点输出片段:', {k: node_output.get(k) for k in debug_keys if k in node_output})
                
                    # 合并当前节点的状态更新到总状态中
                    # 对于列表类字段（如 errors / trace），LangGraph 已在内部负责合并
                    # 这里简单覆盖即可，保留其他节点写入的字段
                    result_state.update(node_output)
        
        # 调试日志：打印最终聚合状态
        # [DEBUG] print('[DEBUG] 最终 result_state 关键信息:', {k: result_state.get(k) for k in ['company_name', 'intent', 'need_financial', 'need_listing', 'financial_data', 'listing_data', 'card_json', 'errors']})
        # [DEBUG] print('=' * 80 + '\n')
        
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
        
        # 提取 AI 回复内容用于历史记录
        ai_reply_content = ""
        
        if intent == "chat":
            # 对话模式：直接返回文本
            chat_reply = result_state.get("chat_reply", "抱歉，我无法理解你的问题。")
            ai_reply_content = chat_reply
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
            
            # 记录 AI 回复内容
            ai_reply_content = "\n".join(output_lines)
            
            # 发送格式化后的结果
            await cl.Message(content=ai_reply_content).send()
        
        # 更新会话历史（在流程结束后）
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": ai_reply_content})
        cl.user_session.set("history", history)
        
        # ==================== 消息保存说明 ====================
        # 注意：Chainlit 框架会自动调用 create_step 保存消息
        # 我们不需要手动保存，否则会导致重复
        thread_id = cl.context.session.thread_id
        
        # ==================== 智能更新会话名称 ====================
        # 获取当前会话信息，如果名称是默认值则更新
        current_thread = await data_layer.get_thread(thread_id)
        current_name = current_thread.get("name", "") if current_thread else ""
        
        # 只有当会话名称是默认值时才更新
        if current_name in ["New Chat", "", None]:
            company_name = result_state.get("company_name", "")
            if company_name and company_name != "未知":
                thread_name = f"Query: {company_name}"
            else:
                # 使用用户第一条查询的前30个字符
                query_preview = user_query[:30].replace("\n", " ")
                thread_name = f"Chat: {query_preview}" + ("..." if len(user_query) > 30 else "")
            
            print(f"\n[on_message] 更新会话名称: '{thread_name}'")
            await data_layer.update_thread(thread_id, name=thread_name)
            print(f"[on_message] ✓ 会话名称已更新\n")
        
        print(f"[on_message] ✓ 消息已保存到数据层，会话ID: {thread_id}")
    
    except Exception as e:
        # 错误处理
        error_msg = f"❌ 处理过程中发生错误：\n```\n{str(e)}\n```"
        await cl.Message(content=error_msg).send()


if __name__ == "__main__":
    # Chainlit 会通过命令行启动，不需要手动运行
    pass
