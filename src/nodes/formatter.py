from __future__ import annotations

"""
formatter 节点：数据格式化与卡片生成器

它在整个流程中的位置：
- 所有并行工具节点（financial_tool、listing_tool）完成后汇聚到这里
- 读取 state 中收集好的所有数据
- 根据 intent 类型决定输出格式：
  * chat: 生成对话回复
  * financial/listing: 生成前端展示卡片 JSON
- 输出最终结果到 state.card_json

职责说明：
这是整个 Agent 流程的最后一站，把散落在 state 各处的数据整理成
前端能直接渲染的格式。就像是把食材做成一道菜端上桌。
"""

from typing import Any, Dict, List
from pathlib import Path

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from ..models import get_chat_model
from ..state import State


def load_assistant_prompt() -> str:
    """
    加载对话助手提示词
    
    从 src/prompts/assistant.yaml 读取系统提示词
    用于 intent=chat 时生成回复
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "assistant.yaml"
    if not prompt_path.exists():
        # 如果文件不存在，使用默认提示词
        return "你是一个友好的助手，简洁回答用户的问题。"
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_config = yaml.safe_load(f)
    
    return prompt_config.get("content", "你是一个友好的助手。").strip()


def generate_chat_reply(state: State) -> str:
    """
    生成对话回复
    
    当 intent=chat 时调用，使用轻量级模型生成自然对话回复
    """
    # 如果已经有回复了，直接返回
    if state.get("chat_reply"):
        return state["chat_reply"]
    
    # 如果前置节点已经出错,直接返回错误提示,避免再次调用LLM浪费时间
    errors = state.get("errors", [])
    if errors:
        # 提取第一个错误的关键信息
        first_error = errors[0]
        if "Request timed out" in first_error or "timeout" in first_error.lower():
            return "抱歉,网络请求超时了,请检查网络连接或稍后再试。"
        return f"抱歉,系统遇到了一些问题: {first_error}"
    
    try:
        # 加载提示词
        system_prompt = load_assistant_prompt()
        
        # 构造消息
        llm = get_chat_model()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_query"])
        ]
        
        # 调用模型
        print(f"[INFO] formatter 调用 LLM 生成对话回复...")
        response = llm.invoke(messages)
        return response.content.strip()
        
    except Exception as e:
        # 降级回复
        print(f"[ERROR] formatter 生成对话失败: {str(e)}")
        return f"抱歉，我现在无法处理你的请求。（{str(e)}）"


def build_financial_section(state: State) -> List[Dict[str, Any]]:
    """
    构建财务数据区块
    
    从 state.financial_data 提取数据，格式化为卡片的一个 section
    """
    sections = []
    financial_data = state.get("financial_data")
    
    if not financial_data:
        return sections
    
    # 构建财务信息卡片
    section = {
        "title": "财务数据",
        "items": [
            {"label": "市值", "value": financial_data.get("market_cap", "未知")},
            {"label": "利润", "value": financial_data.get("profit", "未知")},
        ],
        "source": financial_data.get("source", "未知")
    }
    
    sections.append(section)
    return sections


def build_listing_section(state: State) -> List[Dict[str, Any]]:
    """
    构建上市信息区块
    
    从 state.listing_data 提取数据，格式化为卡片的一个 section
    """
    sections = []
    listing_data = state.get("listing_data")
    
    if not listing_data:
        return sections
    
    # 构建上市信息卡片
    section = {
        "title": "上市信息",
        "items": [
            {"label": "上市日期", "value": listing_data.get("listed_date", "未知")},
            {"label": "上市状态", "value": listing_data.get("listing_status", "未知")},
            {"label": "交易板块", "value": listing_data.get("board", "未知")},
        ],
        "source": listing_data.get("source", "未知")
    }
    
    sections.append(section)
    return sections


def build_error_section(state: State) -> List[Dict[str, str]]:
    """
    构建错误提示区块
    
    如果执行过程中有错误，生成警告信息
    """
    errors = state.get("errors", [])
    if not errors:
        return []
    
    return [{
        "type": "warning",
        "message": "部分数据获取失败：" + "; ".join(errors)
    }]


def formatter_node(state: State) -> State:
    """
    Formatter 节点：格式化输出
    
    职责：
    1. 判断 intent 类型
    2. 如果是 chat：生成对话回复，输出为文本格式
    3. 如果是 financial/listing：组装数据卡片，输出为 JSON 格式
    4. 处理错误和警告信息
    5. 记录 trace
    
    输入：state（读取多个字段）
    输出：state.card_json 或 state.chat_reply
    """
    intent = state.get("intent", "chat")
    
    # 步骤1：判断意图类型
    if intent == "chat":
        # 对话模式：生成文本回复
        chat_reply = generate_chat_reply(state)
        state["chat_reply"] = chat_reply
        
        # 构造简单的 chat 卡片
        state["card_json"] = {
            "type": "chat",
            "text": chat_reply
        }
        
        state["trace"].append("formatter 完成 (chat 模式)")
        return state
    
    # 步骤2：构造金融卡片 JSON 骨架
    card: Dict[str, Any] = {
        "type": "fin_card",
        "company": state.get("company_name", "未知公司"),
        "sections": []
    }
    
    # 步骤3：填充 financial 数据
    financial_sections = build_financial_section(state)
    card["sections"].extend(financial_sections)
    
    # 步骤4：填充 listing 数据
    listing_sections = build_listing_section(state)
    card["sections"].extend(listing_sections)
    
    # 步骤5：追加错误信息（如果有）
    error_sections = build_error_section(state)
    if error_sections:
        card["warnings"] = error_sections
    
    # 如果没有任何数据，添加提示
    if not card["sections"]:
        card["sections"].append({
            "title": "提示",
            "items": [
                {"label": "状态", "value": "未找到相关数据"}
            ],
            "source": "系统"
        })
    
    # 写入 state
    state["card_json"] = card
    
    # 步骤6：记录 trace
    sections_count = len(card["sections"])
    state["trace"].append(f"formatter 完成 (生成 {sections_count} 个数据区块)")
    
    return state