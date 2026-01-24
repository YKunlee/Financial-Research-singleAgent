# 中文伪代码：LLM 分析意图，提取公司名

# 输入: state.user_query
# 输出: 更新 state.company_name, state.intent, state.need_financial, state.need_listing

# 步骤1：加载提示词（src/prompts/analyzer.yaml）
# 步骤2：构造 LLM 输入
#   - 传入 user_query
#   - 约束输出结构：company_name, intent, need_financial, need_listing, confidence
# 步骤3：调用 LLM
# 步骤4：解析结构化输出
#   - 若 company_name 为空 且 intent 非 chat：
#       intent = chat
#       need_financial = false
#       need_listing = false
# 步骤5：写回 state
#   - state.company_name = 解析结果
#   - state.intent = 解析结果
#   - state.need_financial = 解析结果
#   - state.need_listing = 解析结果
#   - state.confidence = 解析结果
# 步骤6：记录 trace
#   - state.trace += "analyzer 完成"

# 路由建议（由 graph.py 读取）
# - intent=chat -> 直接进入 formatter 或 chat 处理节点
# - intent=financial/listing -> 进入 fetcher 触发并行工具

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from ..models import get_model
from ..state import State


def load_analyzer_prompt() -> str:
    """
    步骤1：加载提示词文件
    
    从 src/prompts/analyzer.yaml 加载系统提示词
    返回完整的提示词内容
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "analyzer.yaml"
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_config = yaml.safe_load(f)
    
    return prompt_config.get("content", "").strip()


def build_llm_prompt(user_query: str, history: List[Dict[str, str]] = None) -> str:
    """
    步骤2：构造 LLM 输入
    
    将用户查询与输出结构约束组合成完整的提示词
    要求 LLM 返回 JSON 格式的结构化输出
    支持传入对话历史以理解指代关系
    """
    # 构造历史上下文部分
    history_text = ""
    if history:
        history_text = "【对话历史】:\n"
        for msg in history[-10:]:  # 最多取最近10条
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            # 限制每条历史消息长度，避免过长
            if len(content) > 500:
                content = content[:500] + "..."
            history_text += f"{role}: {content}\n"
        history_text += "\n"
    
    return f"""{history_text}【当前用户输入】:{user_query}

请分析以上输入（结合对话历史理解指代关系），提取以下信息并以 JSON 格式返回：

{{
  "company_name": "公司名称（如果有）",
  "intent": "financial | listing | chat",
  "need_financial": true/false,
  "need_listing": true/false,
  "confidence": 0.0-1.0
}}

规则：
1. intent 必须是 "financial"（财务数据）、"listing"（上市信息）或 "chat"（普通对话）之一
2. 如果提到财务、市值、利润等，intent=financial，need_financial=true
3. 如果提到上市、IPO、挂牌等，intent=listing，need_listing=true
4. 如果两者都提到，优先设置为 financial，并将两个 need_* 都设为 true
5. 如果都没提到，intent=chat，两个 need_* 都为 false
6. confidence 表示你对公司名提取的信心程度
7. **如果当前输入使用指代词（如"它"、"该公司"、"这个"），请从对话历史中找到最近提到的公司名**
8. 只返回 JSON，不要其他文字

示例：
输入："腾讯的市值是多少"
输出：{{"company_name":"腾讯","intent":"financial","need_financial":true,"need_listing":false,"confidence":0.95}}

输入（有历史）：
历史："用户: 腾讯的市值是多少"
当前："它的市盈率呢"
输出：{{"company_name":"腾讯","intent":"financial","need_financial":true,"need_listing":false,"confidence":0.90}}

输入："你好"
输出：{{"company_name":null,"intent":"chat","need_financial":false,"need_listing":false,"confidence":0.0}}"""


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    步骤4：解析结构化输出
    
    从 LLM 返回的文本中提取 JSON 结构
    应用业务规则：如果没有公司名且不是 chat，强制转为 chat
    """
    # 清理响应文本，提取 JSON
    response_text = response_text.strip()
    
    # 尝试找到 JSON 部分（可能包含在代码块中）
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        response_text = response_text[start:end].strip()
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        response_text = response_text[start:end].strip()
    
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        # 如果解析失败，降级为 chat 模式
        return {
            "company_name": None,
            "intent": "chat",
            "need_financial": False,
            "need_listing": False,
            "confidence": 0.0
        }
    
    # 步骤4 核心逻辑：若 company_name 为空且 intent 非 chat，强制转为 chat
    company_name = result.get("company_name")
    intent = result.get("intent", "chat")
    
    if not company_name and intent != "chat":
        result["intent"] = "chat"
        result["need_financial"] = False
        result["need_listing"] = False
    
    return result


def analyzer_node(state: State) -> State:
    """
    Analyzer 节点：LLM 意图分析与实体提取
    
    职责：
    1. 调用 LLM 分析用户查询
    2. 提取公司名、意图类型、置信度
    3. 设置并行任务开关（need_financial、need_listing）
    4. 更新 state 并记录 trace
    5. 结合会话历史理解指代关系
    
    输入：state.user_query, state.conversation_history
    输出：更新 state 的多个字段
    """
    try:
        # 步骤1：加载提示词
        system_prompt = load_analyzer_prompt()
        
        # 获取会话历史
        history = state.get("conversation_history", [])
        
        # 步骤2：构造 LLM 输入（传入历史）
        user_prompt = build_llm_prompt(state["user_query"], history)
        
        # 步骤3：调用 LLM
        llm = get_model("analyzer")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        
        # 步骤4：解析结构化输出
        parsed = parse_llm_response(response.content)
        
        # 步骤5：写回 state
        state["company_name"] = parsed.get("company_name")
        state["intent"] = parsed.get("intent", "chat")
        state["confidence"] = parsed.get("confidence", 0.0)
        state["need_financial"] = parsed.get("need_financial", False)
        state["need_listing"] = parsed.get("need_listing", False)
        
        # 步骤6：记录 trace
        state["trace"].append(
            f"analyzer 完成 | 公司:{state['company_name']} | "
            f"意图:{state['intent']} | 置信度:{state['confidence']}"
        )
        
    except Exception as e:
        # 错误处理：记录错误并降级为 chat 模式
        error_msg = f"analyzer 节点错误: {str(e)}"
        
        # 打印详细日志用于诊断
        print(f"[ERROR] {error_msg}")
        print(f"[ERROR] 异常类型: {type(e).__name__}")
        
        # 避免重复添加相同错误
        if error_msg not in state["errors"]:
            state["errors"].append(error_msg)
        state["trace"].append(error_msg)
        
        # 降级到安全的默认值
        state["company_name"] = None
        state["intent"] = "chat"
        state["confidence"] = 0.0
        state["need_financial"] = False
        state["need_listing"] = False
    
    return state
